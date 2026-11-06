"""Sub-agents and the inbox: how a background sub-agent's or script's end, and messages from
other conversations, become a turn of the conversation they belong to, and what
the watching tab hears meanwhile. It lives apart from ChatSessionLG so the rule
that bounds a chain of such turns reads in one place; the session keeps the turn
lock, the sockets and the counters.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from langchain_core.tools import BaseTool

from ..config import Settings
from ..coordinator import CORE_TOOL_NAMES
from ..runtime_lg import (
    SUBAGENT_MAX_STEPS,
    SilentSocket,
    SubAgentHost,
    keeps_tool_list_fixed,
    resolve_chat_model,
    subagent_report,
    tool_name,
)
from ..tools import (
    BackgroundTask,
    BackgroundTaskStore,
    MessagingStore,
    SubAgentTask,
    SubAgentTaskStore,
    WakeStore,
    format_incoming,
    read_background_log,
    running_subagent,
    set_change_listener,
    set_inbox_listener,
)
from .approvals import SubAgentChannel, can_resolve_approvals
from .events import EventSink
from .thread_meta import ThreadMetaStore
from .turn_lock import TurnLock

logger = logging.getLogger(__name__)

_WIND_DOWN_REPORT_TURN = 3
_MAX_REPORT_TURNS_IN_ROW = 5
_MESSAGE_WIND_DOWN_NOTE = (
    "\n\n(Several messages from other conversations have come in without a word from "
    "the user. Tell the user where things stand rather than replying again, unless "
    "they asked for more rounds.)"
)
_WIND_DOWN_NOTE = (
    "\n\n(Several sub-agent reports in a row have come in without a word from the "
    "user. Tell the user where things stand now rather than starting more sub-agents, "
    "unless they asked for more rounds.)"
)
_TASK_WIND_DOWN_NOTE = (
    "\n\n(Several reports in a row have come in without a word from the user. Tell the "
    "user where things stand now rather than starting more background work, unless they "
    "asked for more rounds.)"
)

# Starts the message a finished background script or command sends its conversation; the chat
# draws such a message as a notice rather than the user's words.
BACKGROUND_REPORT_PREFIX = "[Background task finished]"
_REPORT_TAIL_BYTES = 6000
_OUTCOMES = {
    "succeeded": "finished",
    "timed_out": "ran out of time and was stopped",
    "killed": "was stopped by the user",
    "interrupted": "was cut off when coscribe closed",
}


def background_report(state_dir: str | Path, task: BackgroundTask, reasons: list[str]) -> str:
    """The message a background script's or command's end sends its conversation."""
    outcome = _OUTCOMES.get(task.status, f"failed with exit code {task.exit_code}")
    body = f'{BACKGROUND_REPORT_PREFIX} "{task.description}" (task {task.task_id}) {outcome}.'
    log = read_background_log(state_dir, task.task_id, _REPORT_TAIL_BYTES)
    output = str(log["output"]).strip() if log else ""
    body += f" The end of its output:\n\n{output}" if output else " It printed nothing."
    for reason in reasons:
        body += f"\n\nYou asked to be woken for it to: {reason}"
    return body


class SubAgentApprovalChannel(SubAgentChannel):
    """Stands in for the websocket when a sub-agent's call is decided: an
    approval it needs is recorded on its task (the panel shows it from
    there), announced to the watching tab, and forwarded to the turn's own
    socket when no tab is watching -- the CLI answers approvals right
    inside send_json."""

    def __init__(self, session: SubAgentChannelHost, task: SubAgentTask) -> None:
        self._session = session
        self._task = task

    @property
    def delegated_task(self) -> str:
        return self._task.prompt

    @property
    def task_id(self) -> str:
        return self._task.task_id

    @property
    def can_resolve_approvals(self) -> bool:
        socket = self._session._live_websocket or self._session._turn_websocket
        return socket is not None and can_resolve_approvals(socket)

    async def send_json(self, payload: dict[str, Any]) -> None:
        if payload.get("type") != "approval_required":
            return
        task = self._task
        task.pending_approval = {k: v for k, v in payload.items() if k != "type"}
        task.status = "needs_approval"
        SubAgentTaskStore(self._session.settings.state_dir).save(task)
        await self._session._subagent_changed(task)
        socket = self._session._live_websocket or self._session._turn_websocket
        if socket is None:
            return
        try:
            await socket.send_json(
                {**payload, "subagent_id": task.task_id, "subagent": task.description}
            )
        except Exception:  # noqa: BLE001 -- e.g. the finished turn's closed socket
            # The approval waits on the task; the panel shows it when opened.
            logger.debug("sub-agent approval not forwarded", exc_info=True)


class SubAgentChannelHost(Protocol):
    """What a sub-agent's approval channel reads on the session."""

    settings: Settings
    _live_websocket: EventSink | None
    _turn_websocket: Any

    async def _subagent_changed(self, task: SubAgentTask) -> None: ...


class SubAgentSessionHost(SubAgentChannelHost, Protocol):
    """What the reports read and call on the session they report to."""

    thread_id: str
    settings: Settings
    hooks_config: dict[str, list[str]]
    _base_tools: list[Callable[..., Any] | BaseTool]
    _model_string: str
    _custom_providers: Any
    _configured_models: Callable[[], list[str]]
    _live_websocket: EventSink | None
    _turn_lock: TurnLock
    _current_turn_task: asyncio.Task[None] | None
    _reporting_subagents: set[str]
    _report_tasks: set[asyncio.Task[None]]
    _report_turns_in_row: int
    _delivering_inbox: bool
    _loop: asyncio.AbstractEventLoop | None

    def is_workflow_run(self) -> bool: ...

    async def notify_resync(self) -> None: ...

    async def _decide_action_request(
        self, request: dict[str, Any], websocket: Any, *, honor_stop: bool = True
    ) -> Any: ...

    async def _handle_user_message_locked(
        self,
        text: str,
        websocket: EventSink,
        images: list[str] | None = None,
        *,
        notice: bool = False,
        artifact: str | None = None,
        design_system: dict[str, Any] | None = None,
    ) -> None: ...


class SubAgentReporter:
    def __init__(self, host: SubAgentSessionHost) -> None:
        self._host = host

    def listen(self) -> None:
        set_change_listener(self._host.thread_id, self._background_task_changed)
        set_inbox_listener(self._host.thread_id, self.schedule_inbox_delivery)

    def _subagent_host(self, model: Any) -> SubAgentHost:
        def resolve_model(requested: str) -> tuple[str, Any]:
            if not requested or requested == self._host._model_string:
                return self._host._model_string, model
            configured = self._host._configured_models()
            if requested not in configured:
                raise ValueError(
                    f"{requested!r} isn't a configured model. Configured: {', '.join(configured)}"
                )
            return requested, resolve_chat_model(requested, self._host._custom_providers)

        async def decide(request: dict[str, Any], task: SubAgentTask) -> Any:
            channel = SubAgentApprovalChannel(self._host, task)
            return await self._host._decide_action_request(request, channel, honor_stop=False)

        return SubAgentHost(
            thread_id=self._host.thread_id,
            state_dir=Path(self._host.settings.state_dir),
            resolve_model=resolve_model,
            configured_models=self._host._configured_models,
            decide=decide,
            changed=self._subagent_changed,
            defer_tools=self._host.settings.defer_tools,
            core_tool_names=CORE_TOOL_NAMES,
            fixed_tool_names=frozenset(tool_name(t) for t in self._host._base_tools),
            keeps_tool_list_fixed=lambda child_model: keeps_tool_list_fixed(
                child_model, self._host._custom_providers
            ),
            interrupt_all=bool(self._host.hooks_config["PreToolUse"]),
            max_turns=SUBAGENT_MAX_STEPS,
            background_allowed=lambda: self._host.settings.background_agents,
        )

    async def _subagent_changed(self, task: SubAgentTask) -> None:
        # Before any await: the wake poller runs on this loop too, and must
        # not also resume the thread for a wake this report takes over.
        # A stop the model asked for itself needs no report.
        ended = task.status in ("succeeded", "failed") or (
            task.status == "stopped" and task.stopped_by == "user"
        )
        if (
            task.background
            and ended
            and not task.reported
            and task.task_id not in self._host._reporting_subagents
        ):
            self._host._reporting_subagents.add(task.task_id)
            reasons = self._take_wakes("subagent", task.task_id)
            report = asyncio.create_task(self._report_subagent(task.task_id, reasons))
            self._host._report_tasks.add(report)
            report.add_done_callback(self._host._report_tasks.discard)
        websocket = self._host._live_websocket
        if websocket is None:
            return
        try:
            await websocket.send_json(
                {"type": "subagents_changed", "task_id": task.task_id, "status": task.status}
            )
        except Exception:  # noqa: BLE001 -- a closing tab mustn't fail the sub-agent's run
            logger.debug("subagents_changed not delivered", exc_info=True)

    def _background_task_changed(self, task: BackgroundTask) -> None:
        # Before any await, like a sub-agent's: the wake poller must not also resume the thread.
        if (
            task.status != "running"
            and not task.reported
            and task.task_id not in self._host._reporting_subagents
        ):
            self._host._reporting_subagents.add(task.task_id)
            reasons = self._take_wakes("task", task.task_id)
            report = asyncio.get_running_loop().create_task(
                self._report_background_task(task.task_id, reasons)
            )
            self._host._report_tasks.add(report)
            report.add_done_callback(self._host._report_tasks.discard)
        websocket = self._host._live_websocket
        if websocket is None:
            return
        message = {
            "type": "background_tasks_changed",
            "task_id": task.task_id,
            "status": task.status,
        }
        notice = asyncio.get_running_loop().create_task(self._send_quietly(websocket, message))
        self._host._report_tasks.add(notice)
        notice.add_done_callback(self._host._report_tasks.discard)

    @staticmethod
    async def _send_quietly(websocket: EventSink, message: dict[str, Any]) -> None:
        try:
            await websocket.send_json(message)
        except Exception:  # noqa: BLE001 -- a closing tab mustn't fail the script's run
            logger.debug("%s not delivered", message["type"], exc_info=True)

    def _take_wakes(self, kind: str, task_id: str) -> list[str]:
        wake_store = WakeStore(self._host.settings.state_dir)
        reasons = []
        for wake in wake_store.list_pending():
            waits_on = wake.subagent_task_id if kind == "subagent" else wake.task_id
            if wake.thread_id == self._host.thread_id and wake.kind == kind and waits_on == task_id:
                wake.status = "woken"
                wake.woken_at = datetime.now(UTC).isoformat()
                wake_store.save(wake)
                reasons.append(wake.reason)
        return reasons

    async def _report_subagent(self, task_id: str, reasons: list[str]) -> None:
        """Tells the conversation how a background sub-agent ended. Skipped if the model
        already read the outcome itself in the meantime."""

        def claim() -> str | None:
            store = SubAgentTaskStore(self._host.settings.state_dir)
            task = store.load(task_id)
            if task is None or task.reported:
                return None
            task.reported = True
            store.save(task)
            return subagent_report(task, reasons)

        await self._report(task_id, claim, _WIND_DOWN_NOTE)

    async def _report_background_task(self, task_id: str, reasons: list[str]) -> None:
        """Tells the conversation how a background script or command ended, with the end of
        its output, so the model carries on without polling or asking to be woken."""
        state_dir = self._host.settings.state_dir

        def claim() -> str | None:
            store = BackgroundTaskStore(state_dir)
            task = store.load(task_id)
            if task is None or task.status == "running" or task.reported:
                return None
            task.reported = True
            store.save(task)
            return background_report(state_dir, task, reasons)

        await self._report(task_id, claim, _TASK_WIND_DOWN_NOTE)

    async def _report(
        self, task_id: str, claim: Callable[[], str | None], wind_down_note: str
    ) -> None:
        """Sends a report as a turn of its own -- after the turn in progress, if there is one,
        so the model hears it at its next chance rather than never. Past the cap of report
        turns without the user it stays unreported, for the model to find once the user is
        back."""
        try:
            async with self._host._turn_lock:
                if self._host.is_workflow_run():
                    return
                if self._host._report_turns_in_row >= _MAX_REPORT_TURNS_IN_ROW:
                    logger.info(
                        "%s not reported to %s: %d report turns without the user",
                        task_id,
                        self._host.thread_id,
                        self._host._report_turns_in_row,
                    )
                    await self._host.notify_resync()
                    return
                text = claim()
                if text is None:
                    logger.info(
                        "%s not reported to %s: gone or already read", task_id, self._host.thread_id
                    )
                    return
                self._host._report_turns_in_row += 1
                if self._host._report_turns_in_row >= _WIND_DOWN_REPORT_TURN:
                    text += wind_down_note
                websocket: Any = self._host._live_websocket
                if websocket is not None:
                    try:
                        await websocket.send_json({"type": "turn_started", "text": text})
                    except Exception:  # noqa: BLE001 -- the tab went away; run unwatched
                        websocket = None
                self._host._current_turn_task = asyncio.current_task()
                socket: Any = websocket or SilentSocket()
                await self._host._handle_user_message_locked(text, socket, notice=True)
            if websocket is None:
                await self._host.notify_resync()
        except Exception:
            logger.exception("reporting %s to its conversation failed", task_id)
        finally:
            self._host._reporting_subagents.discard(task_id)

    def schedule_inbox_delivery(self) -> None:
        """Messages from other conversations are waiting: turn them into a turn
        of this one, once. Callable from a tool thread or a connect, with or
        without a running loop (then they wait for the next call)."""
        if self._host._delivering_inbox or self._host.is_workflow_run():
            return
        if MessagingStore(self._host.settings.state_dir).pending(self._host.thread_id) == 0:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # A sync tool runs in a worker thread: hand over to the server's loop.
            if self._host._loop is not None and not self._host._loop.is_closed():
                self._host._loop.call_soon_threadsafe(self.schedule_inbox_delivery)
            return
        self._host._loop = loop
        self._host._delivering_inbox = True
        task = loop.create_task(self._deliver_inbox())
        self._host._report_tasks.add(task)
        task.add_done_callback(self._host._report_tasks.discard)

    async def _deliver_inbox(self) -> None:
        """Tells the conversation what other conversations sent it, as a turn of
        its own after the one in progress. Bounded like sub-agent reports: past
        the cap the messages stay in the inbox until the user next speaks."""
        store = MessagingStore(self._host.settings.state_dir)
        # A message that arrives during the turn it started needs another one.
        again = True
        try:
            async with self._host._turn_lock:
                if self._host._report_turns_in_row >= _MAX_REPORT_TURNS_IN_ROW:
                    again = False
                    await self._host.notify_resync()
                    return
                messages = store.take_all(self._host.thread_id)
                if not messages:
                    return
                self._host._report_turns_in_row += 1
                text = format_incoming(messages)
                if self._host._report_turns_in_row >= _WIND_DOWN_REPORT_TURN:
                    text += _MESSAGE_WIND_DOWN_NOTE
                ThreadMetaStore(self._host.settings.state_dir).update(
                    self._host.thread_id, archived=False
                )
                websocket: Any = self._host._live_websocket
                if websocket is not None:
                    try:
                        await websocket.send_json({"type": "turn_started", "text": text})
                    except Exception:  # noqa: BLE001 -- the tab went away; run unwatched
                        websocket = None
                self._host._current_turn_task = asyncio.current_task()
                await self._host._handle_user_message_locked(
                    text, websocket or SilentSocket(), notice=True
                )
            if websocket is None:
                await self._host.notify_resync()
        except Exception:
            again = False
            logger.exception("delivering messages from other conversations failed")
        finally:
            self._host._delivering_inbox = False
            if again:
                self.schedule_inbox_delivery()

    def _stop_waited_on_subagents(self) -> None:
        """Stop the sub-agents a turn is waiting on; background ones were
        handed off and keep going."""
        for task in SubAgentTaskStore(self._host.settings.state_dir).list_for_thread(
            self._host.thread_id
        ):
            runner = running_subagent(task.task_id)
            if runner is not None and not task.background:
                runner.cancel()
