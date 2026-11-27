from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Any, NamedTuple, Protocol

from .wire import SteersDeliveredEvent


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


class QueuedSteer(NamedTuple):
    id: str
    text: str
    images: list[str]
    sent_at: str

    @classmethod
    def capture(cls, key: str, text: str, images: list[str] | None) -> QueuedSteer:
        return cls(key, text, list(images or []), datetime.now(UTC).isoformat(timespec="seconds"))


async def deliver_steers(
    socket: EventSink | None, steers: list[QueuedSteer]
) -> list[tuple[str, list[str], str]]:
    if socket is not None:
        sent_at_by_id = {note.id: note.sent_at for note in steers}
        event = SteersDeliveredEvent(
            type="steers_delivered", ids=list(sent_at_by_id), sent_at_by_id=sent_at_by_id
        )
        with contextlib.suppress(Exception):  # The tab went away while the model took the notes.
            await socket.send_json(event)
    return [(note.text, note.images, note.sent_at) for note in steers]
