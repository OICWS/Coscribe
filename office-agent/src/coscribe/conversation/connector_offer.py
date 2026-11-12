"""The tools that let a conversation suggest a connector when the work needs a service it can't
reach, and what each conversation was offered (decision 0046). The catalog belongs to the
server, so it comes in as a `ConnectorDirectory`; the card the person answers is drawn from
`offer_connector`'s result, so it survives a reload like any other tool call."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Literal, Protocol

from ..runtime import tool_metadata

CONNECTED_NOTE_PREFIX = "[Connector connected]"
_MAX_FOUND = 3


class ConnectorDirectory(Protocol):
    """The server's connector catalog and the state of each connector in it. `state` is one of
    "connected", "signed_out" (added, and its sign-in no longer works), "not_connected"
    (added, not reachable now), "needs_setup" (needs the person's own registered app first)
    or "available"."""

    def search(self, need: str, limit: int) -> list[dict[str, Any]]: ...

    def card(self, name: str) -> dict[str, Any] | None: ...


class OfferLog:
    """Per conversation, the connectors offered, turned down and connected since, so a "Not
    now" holds for the rest of that conversation, and a connection wakes only the conversations
    that offered that connector, once."""

    _lock = threading.Lock()

    def __init__(self, state_dir: str | Path) -> None:
        self.path = Path(state_dir) / "connector_offers.json"

    def _load(self) -> dict[str, dict[str, str]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def state(self, thread_id: str, name: str) -> str | None:
        return self._load().get(thread_id, {}).get(name)

    def waiting(self, connected: Iterable[str]) -> list[tuple[str, str]]:
        """(conversation, connector) for each offer still open whose connector is connected."""
        names = set(connected)
        return [
            (thread_id, name)
            for thread_id, offers in self._load().items()
            for name, state in offers.items()
            if state == "offered" and name in names
        ]

    def mark(
        self, thread_id: str, name: str, state: Literal["offered", "declined", "connected"]
    ) -> None:
        with self._lock:
            data = self._load()
            data.setdefault(thread_id, {})[name] = state
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data), encoding="utf-8")

    def forget(self, thread_id: str) -> None:
        with self._lock:
            data = self._load()
            if data.pop(thread_id, None) is not None:
                self.path.write_text(json.dumps(data), encoding="utf-8")


def connected_note(title: str) -> str:
    """The message a conversation that offered a connector gets once it is connected."""
    return (
        f"{CONNECTED_NOTE_PREFIX} The user connected {title}, which you offered. Its "
        "tools are available now: find them with search_tools and carry on with what the user "
        "asked for."
    )


def build_connector_offer_tools(
    directory: ConnectorDirectory,
    state_dir: str | Path,
    thread_id: str,
    is_workflow_run: Callable[[], bool],
) -> list[Callable[..., Any]]:
    """`find_connector` and `offer_connector`, both deferred, so the fixed tool list (0001)
    keeps its shape."""
    log = OfferLog(state_dir)

    def find_connector(need: str) -> list[dict[str, Any]]:
        """Find connectors that would give you a service this conversation can't reach yet,
        such as Notion, Jira or a CRM. Call it when the user's request needs one and no tool
        you have reaches it (look with search_tools first). Each result has "name", "title",
        "description" and "state": "connected" means its tools already exist (find them with
        search_tools); otherwise suggest it to the user with offer_connector. An empty list
        means the built-in list has nothing for it: say the user can add it as a custom
        connector in Settings > Connectors, and never make up an address for it.

        Args:
            need: the service or the kind of work, in a few English words ("Notion pages",
                "Jira issues").
        """
        return directory.search(need, _MAX_FOUND)

    def offer_connector(name: str, why: str) -> dict[str, Any]:
        """Show the user a card that offers to connect a connector find_connector returned.
        The user signs in on their own; nothing is connected until they do. After calling it,
        say in one sentence what you will do once it is connected and end your turn without
        doing the work another way: when the user connects it you get a new message and carry
        on then, so don't ask them to tell you.

        Args:
            name: the connector's "name" from find_connector.
            why: one sentence, in the language the user writes in, on what it lets you do
                for this request.
        """
        if is_workflow_run():
            return {
                "status": "refused",
                "error": "Nobody is watching this run to connect anything; name the connector "
                "that would help in your result instead.",
            }
        card = directory.card(name)
        if card is None:
            return {
                "status": "refused",
                "error": f"No connector is named {name!r}; use a name find_connector returned.",
            }
        if card["state"] == "connected":
            return {
                "status": "connected",
                "note": f"{card['title']} is connected already; find its tools with search_tools.",
            }
        if log.state(thread_id, name) == "declined":
            return {
                "status": "declined",
                "error": f"The user said not now to {card['title']} in this conversation; don't "
                "offer it again unless they ask for it.",
            }
        log.mark(thread_id, name, "offered")
        return {"status": "offered", **card, "why": why.strip()[:300]}

    return [
        tool_metadata(find_connector, risk_category="READ", category="connectors"),
        tool_metadata(offer_connector, risk_category="READ", category="connectors"),
    ]
