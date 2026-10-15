"""Settling the approvals a paused graph is waiting on, and picking a paused graph up again
after the connection that started it went away."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from langgraph.types import Command

from ..config import Settings
from ..runtime_lg import EXEC_POLICY_TOOL_NAMES, AutoApproveReason, ExecPolicy
from ..tools import (
    QUESTION_TOOL_NAMES,
    TASK_DRAFT_TOOL_NAMES,
    ScheduledTriggerStore,
    parse_run_thread_id,
)
from .approvals import can_resolve_approvals
from .events import EventSink
from .history import close_orphaned_tool_calls
from .turn_lock import TurnLock
from .turn_text import format_reply, usage_event


class ApprovalResumeHost(Protocol):
    """What resolving and resuming read and call on the session they belong to."""

    thread_id: str
    settings: Settings
    config: dict[str, Any]
    lg_agent: Any
    plan_mode: bool
    _gated_tool_risks: dict[str, str]
    _stop_requested: bool
    _turn_lock: TurnLock
    _current_turn_task: asyncio.Task[None] | None
    _turn_websocket: Any
    _last_usage_metadata: Any

    def is_workflow_run(self) -> bool: ...

    def _auto_approves(self, name: str) -> AutoApproveReason | None: ...

    def _auto_review_active(self) -> bool: ...

    def _load_exec_policy(self) -> ExecPolicy: ...

    async def _decide_action_request(self, request: dict[str, Any], websocket: Any) -> Any: ...

    async def _stream_turn(self, turn_input: Any, websocket: EventSink) -> str: ...


class ApprovalResumer:
    def __init__(self, host: ApprovalResumeHost) -> None:
        self._host = host

    def decidable_unattended(self, request: dict[str, Any]) -> bool:
        """Whether the request can be settled with nobody present other than by refusing for
        lack of a person. A gated call that cannot must stay parked for someone to approve
        later, rather than be rejected and let the run carry on without it."""
        host = self._host
        name = request["name"]
        if name in QUESTION_TOOL_NAMES or name in TASK_DRAFT_TOOL_NAMES:
            return True
        if name not in host._gated_tool_risks or host.plan_mode:
            return True
        if host._auto_approves(name) is not None:
            return True
        if host._auto_review_active():
            return True
        if name in EXEC_POLICY_TOOL_NAMES:
            decision, _ = host._load_exec_policy().decide(request["args"].get("script", ""))
            return decision != "prompt"
        return False

    async def resolve_pending_approvals(self, websocket: EventSink) -> str | None:
        """While the graph is paused, decide every pending action request and resume, in a
        loop because a resumed turn can hit another gated call at once.

        Returns the last resumed call's narration, not every round joined: each round already
        streamed its own text as a bubble, so joining them duplicates it in the final reply,
        glued together with no separator. None, not "", when nothing was pending, so a caller
        can tell "nothing to resolve, keep your text" from "resolved, and the model said
        nothing further".

        Several tasks can be pending at once (two spawn_agent calls in one model message).
        LangGraph then requires `Command(resume={interrupt_id: value})` per interrupt; one
        shared value raises. They are decided one after another, so a client must answer the
        first approval before the second is sent.
        """
        host = self._host
        agent = host.lg_agent
        config = host.config
        latest_text: str | None = None
        state = await agent.aget_state(config)
        while state.next:
            if not can_resolve_approvals(websocket) and not all(
                self.decidable_unattended(request)
                for task in state.tasks
                for interrupt in task.interrupts
                for request in interrupt.value.get("action_requests", [])
            ):
                break
            resume_map: dict[str, Any] = {}
            for task in state.tasks:
                for interrupt in task.interrupts:
                    action_requests = interrupt.value.get("action_requests", [])
                    decisions = [
                        await host._decide_action_request(request, websocket)
                        for request in action_requests
                    ]
                    resume_map[interrupt.id] = {"decisions": decisions}

            latest_text = await host._stream_turn(Command(resume=resume_map), websocket)
            state = await agent.aget_state(config)
        return latest_text

    async def resume_after_reconnect(self, websocket: EventSink) -> None:
        """If the graph is still paused on an approval from before a dropped connection or a
        restart, redeliver it now: the checkpointer kept the pending state, this runs the
        delivery a fresh turn's approval uses. A no-op when nothing is pending.

        Under the turn lock: this runs as a background task right after connect, and without
        the lock it could race a user message sent at once on the same agent and config."""
        host = self._host
        if host.is_workflow_run():
            return
        async with host._turn_lock:
            host._current_turn_task = asyncio.current_task()
            # So that this connection closing releases the lock too: abandon_orphaned_turn
            # only cancels a turn driven by the socket that went away, and a question
            # redelivered here waits on it.
            host._turn_websocket = websocket
            # A turn hard-cancelled mid-tool also leaves state.next set, but with no
            # interrupt to redeliver; resuming it would re-run that tool, possibly minutes
            # of work the user just stopped.
            await close_orphaned_tool_calls(host.lg_agent, host.config)
            state = await host.lg_agent.aget_state(host.config)
            if not state.next:
                return
            # state.next is truthy, so the resolve loop runs at least once; `or ""` only
            # satisfies the type checker.
            text = await self.resolve_pending_approvals(websocket) or ""
            await self._record_resumed_run_status()
            await websocket.send_json({"type": "agent_message", "text": format_reply(text)})
            if host._last_usage_metadata is not None:
                await websocket.send_json(usage_event(host._last_usage_metadata))
            await websocket.send_json({"type": "tasks_changed"})

    async def _record_resumed_run_status(self) -> None:
        """A scheduled run that parked on an approval ended as "needs_approval"; once the
        approval is resolved and the turn finishes, the run record says how it ended."""
        host = self._host
        parsed = parse_run_thread_id(host.thread_id)
        if parsed is None:
            return
        trigger_id, run_id = parsed
        store = ScheduledTriggerStore(host.settings.state_dir)
        trigger = store.load(trigger_id)
        run = trigger.find_run(run_id) if trigger is not None else None
        if run is None or run.status != "needs_approval":
            return
        state = await host.lg_agent.aget_state(host.config)
        if any(task.interrupts for task in state.tasks):
            return
        store.finish_run(trigger_id, run_id, "stopped" if host._stop_requested else "completed")
