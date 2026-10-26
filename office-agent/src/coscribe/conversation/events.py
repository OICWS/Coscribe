from __future__ import annotations

import contextlib
from typing import Any, Protocol


class EventSink(Protocol):
    """Where a conversation's events go: a browser's WebSocket, or the CLI's own
    terminal stand-in. Only this one method is used."""

    async def send_json(self, data: Any) -> None: ...


class TurnSocket:
    """What a turn started by a tab writes to. A turn outlives the connection that started it (the
    person opens another conversation, which closes this one's socket), so its events go to
    whichever tab has the conversation open now, or nowhere, and it can ask for an approval only
    while one is open."""

    def __init__(self, session: Any, origin: Any) -> None:
        self._session = session
        self.origin = origin

    @property
    def can_resolve_approvals(self) -> bool:
        return bool(self._session._live_websocket is not None)

    async def send_json(self, data: Any) -> None:
        target = self._session._live_websocket
        if target is None:
            return
        with contextlib.suppress(Exception):  # the tab closed between the check and the send
            await target.send_json(data)


def keeps_running(session: Any, websocket: Any) -> bool:
    """Whether the turn a closed socket was driving goes on. One started by a tab does, unless it
    is parked on an approval or question and no tab is left to answer; any other turn is dropped
    with the socket it was given."""
    turn_socket = session._turn_websocket
    origin = getattr(turn_socket, "origin", None)
    if origin is None:
        return bool(turn_socket is not websocket)
    parked = any(
        not f.done()
        for request_id, f in session._pending_approvals.items()
        if request_id not in session._subagent_request_ids
    ) or any(not f.done() for f in session._pending_questions.values())
    return bool(origin is not websocket or session._live_websocket is not None or not parked)
