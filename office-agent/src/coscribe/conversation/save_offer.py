"""After a turn that did a job of several steps, the offer to save it as a workflow or a skill,
so the person can run it again, or on a schedule, without asking for each step.

It is offered at most once per conversation (a marker beside the thread's title in the state
folder), never in a scheduled or workflow run, and only when the side model reads the request
as one someone would do again rather than a one-off question or fix.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any, Protocol

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.constants import TAG_NOSTREAM

from ..config import Settings
from ..runtime_lg import extract_text
from ..tools import parse_run_thread_id
from .activity import (
    _OUTPUT_RISKS,
    _SCRIPT_TOOLS,
    _UNLISTED_TOOLS,
    _script_files,
    _succeeded_calls,
)
from .events import EventSink

MIN_STEPS = 4
OFFER_INSTRUCTIONS = (
    "Someone asked an assistant for a job and it took the steps listed. Decide whether this is "
    "a job they are likely to do again, the same way with other files or dates, or on a "
    "schedule (a weekly report, a monthly export, tidying a folder), rather than a one-off "
    "question, fix or piece of writing. If it is, reply with a short name for it, two to five "
    'words in the language of the request, such as "Weekly sales report". If not, reply NONE. '
    "Reply with the name or NONE only."
)
MAX_NAME_CHARS = 60


def this_turn(messages: list[BaseMessage]) -> list[BaseMessage]:
    """The messages since the person's last one: what the turn that just ended did."""
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return messages[index + 1 :]
    return messages


def changing_steps(messages: list[BaseMessage], catalog: dict[str, Any]) -> list[str]:
    """The succeeded calls that changed something (wrote a file, sent something out, or a script
    that left files), each as the tool's name and the path it worked on. Reading and looking
    around don't count: a job worth saving makes something."""
    steps = []
    for call in _succeeded_calls(messages):
        name, args = call["name"], call["args"]
        metadata = catalog.get(name)
        if name in _SCRIPT_TOOLS:
            changed = bool(_script_files(call["result"]))
        else:
            changed = metadata is not None and metadata.risk_category in _OUTPUT_RISKS
        if changed:
            path = args.get("path")
            steps.append(f"{name} {path}" if isinstance(path, str) and path else name)
    return steps


def clean_name(text: str) -> str:
    lines = text.strip().splitlines()
    name = " ".join(lines[0].split()).strip("\"'“”「」《》.。") if lines else ""
    if not name or name.upper() == "NONE" or len(name) > MAX_NAME_CHARS:
        return ""
    return name


class SaveOfferHost(Protocol):
    settings: Settings
    thread_id: str
    lg_agent: Any
    config: Any
    _stop_requested: bool
    _pending_approvals: dict[str, Any]
    _pending_questions: dict[str, Any]

    def tool_catalog(self) -> dict[str, Any]: ...


class SaveOffer:
    def __init__(self, host: SaveOfferHost, side_model: Any) -> None:
        self._host = host
        self._side_model = side_model
        self._task: asyncio.Task[None] | None = None

    def _marker(self) -> Path:
        return Path(self._host.settings.state_dir) / f"{self._host.thread_id}.save-offered"

    def consider(self, websocket: EventSink, user_text: str) -> None:
        """Called at the end of a turn; looks in the background when it finished its work."""
        host = self._host
        if (
            not host.settings.save_offers
            or host._stop_requested
            or host._pending_approvals
            or host._pending_questions
            or parse_run_thread_id(self._host.thread_id) is not None
            or self._marker().exists()
            or (self._task is not None and not self._task.done())
        ):
            return
        self._task = asyncio.create_task(self._offer(websocket, user_text))

    async def _offer(self, websocket: EventSink, user_text: str) -> None:
        # A failure, or a tab that went away, only means no offer.
        with contextlib.suppress(Exception):
            state = await self._host.lg_agent.aget_state(self._host.config)
            messages = list(state.values.get("messages", [])) if state.values else []
            turn = this_turn(messages)
            steps = changing_steps(turn, self._host.tool_catalog())
            if len(steps) < MIN_STEPS:
                return
            taken = [c for c in _succeeded_calls(turn) if c["name"] not in _UNLISTED_TOOLS]
            reply = await self._side_model().ainvoke(
                [
                    SystemMessage(content=OFFER_INSTRUCTIONS),
                    HumanMessage(
                        content=f"Request: {user_text[:1500]}\n\nSteps:\n" + "\n".join(steps[:30])
                    ),
                ],
                config={"tags": [TAG_NOSTREAM]},
            )
            name = clean_name(extract_text(reply.content))
            if not name:
                return
            self._marker().parent.mkdir(parents=True, exist_ok=True)
            self._marker().write_text(name, encoding="utf-8")
            await websocket.send_json({"type": "save_offer", "steps": len(taken), "name": name})
