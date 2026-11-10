"""Calls one answer makes to an order-keeping tool run in the order the model wrote them.

LangGraph runs the tool calls of one answer at the same time, a plain function in a thread each.
For `task_create` that left the plan's order, and which task got which id, to thread scheduling:
eight tasks written as 1 to 8 could be listed 6, 4, 2, 7, and the ids the model then updates by
were not the ones it expected. Each such call here waits for the one before it in the answer.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Iterable
from contextlib import suppress
from typing import Any

from langchain.agents.middleware import AgentMiddleware

IN_ORDER = frozenset({"task_create"})
# A call that never gets here (its graph was cancelled, another middleware answered for it)
# must not hold the ones after it for good.
_WAIT_SECONDS = 30.0


def _answer_calls(state: Any) -> list[dict[str, Any]]:
    messages = state.get("messages") if isinstance(state, dict) else getattr(state, "messages", [])
    for message in reversed(messages or []):
        calls = getattr(message, "tool_calls", None)
        if calls:
            return list(calls)
    return []


class CallOrderMiddleware(AgentMiddleware):
    def __init__(self, names: Iterable[str] = IN_ORDER) -> None:
        super().__init__()
        self._names = frozenset(names)
        self._ended: dict[str, Any] = {}
        self._lock = threading.Lock()

    def _places(self, request: Any, event: Callable[[], Any]) -> tuple[str | None, Any, Any]:
        """The id of the call before this one, the event it sets when it ends, and this
        call's own event; all None for a call that waits for nothing and is waited for by none."""
        call = request.tool_call
        if call["name"] not in self._names:
            return None, None, None
        ids = [c["id"] for c in _answer_calls(request.state) if c["name"] in self._names]
        if call["id"] not in ids:
            return None, None, None
        place = ids.index(call["id"])
        with self._lock:
            before = ids[place - 1] if place else None
            waits_for = self._ended.setdefault(before, event()) if before else None
            mine = self._ended.setdefault(call["id"], event()) if place + 1 < len(ids) else None
        return before, waits_for, mine

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        before, waits_for, mine = self._places(request, threading.Event)
        if before is not None:
            waits_for.wait(_WAIT_SECONDS)
            self._ended.pop(before, None)
        try:
            return handler(request)
        finally:
            if mine is not None:
                mine.set()

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        before, waits_for, mine = self._places(request, asyncio.Event)
        if before is not None:
            with suppress(TimeoutError):
                await asyncio.wait_for(waits_for.wait(), _WAIT_SECONDS)
            self._ended.pop(before, None)
        try:
            return await handler(request)
        finally:
            if mine is not None:
                mine.set()
