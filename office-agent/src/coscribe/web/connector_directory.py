"""The connector catalog as a conversation sees it when it suggests a connector (decision 0046):
a search over the Discover entries and each one's state now. Only names and descriptions leave
here; how to connect is read from the catalog again when the person presses Connect."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from ..config import Settings
from ..conversation import OfferLog, connected_note
from ..runtime_lg import McpOAuth
from .connector_catalog import MCP_CATALOG, SeenTools

# Words that say nothing about which service is meant.
_STOPWORDS = frozenset(
    "a an and app my of on or the to in for with from into our your data account "
    "service tool tools connector".split()
)
_WEIGHTS = (("name", 6), ("title", 6), ("category", 3), ("description", 2), ("about", 1))


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1} - _STOPWORDS


def catalog_entry(name: str) -> dict[str, Any] | None:
    return next((e for e in MCP_CATALOG if e["name"] == name), None)


class CatalogDirectory:
    """`ConnectorDirectory` over `MCP_CATALOG`, the live connections and the saved sign-ins."""

    def __init__(self, settings: Settings, connections: Mapping[str, Any], oauth: McpOAuth) -> None:
        self._settings = settings
        self._connections = connections
        self._oauth = oauth

    def _configured(self) -> dict[str, Any]:
        path = self._settings.mcp_config_path
        try:
            raw = json.loads(path.read_text(encoding="utf-8")) if path else {}
        except (OSError, ValueError):
            return {}
        servers = raw.get("mcpServers") if isinstance(raw, dict) else None
        return servers if isinstance(servers, dict) else {}

    def state(self, entry: dict[str, Any], configured: dict[str, Any]) -> str:
        name = entry["name"]
        if name in self._connections:
            return "connected"
        if name in configured:
            return "signed_out" if configured[name].get("auth") == "oauth" else "not_connected"
        setup = entry.get("setup")
        if setup and self._oauth.app(setup["group"]) is None:
            return "needs_setup"
        return "available"

    def _summary(self, entry: dict[str, Any], configured: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": entry["name"],
            "title": entry.get("title", entry["name"]),
            "description": entry.get("description", ""),
            "state": self.state(entry, configured),
        }

    def search(self, need: str, limit: int) -> list[dict[str, Any]]:
        wanted = _words(need)
        scored = []
        for entry in MCP_CATALOG:
            score = 0
            for field, weight in _WEIGHTS:
                score += weight * len(wanted & _words(str(entry.get(field, ""))))
            score += len(wanted & _words(" ".join(entry.get("tools", [])).replace("_", " ")))
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda pair: -pair[0])
        configured = self._configured()
        return [self._summary(entry, configured) for _, entry in scored[:limit]]

    def card(self, name: str) -> dict[str, Any] | None:
        entry = catalog_entry(name)
        if entry is None:
            return None
        tools = SeenTools(self._settings.state_dir).load().get(name) or entry.get("tools", [])
        return {
            **self._summary(entry, self._configured()),
            "category": entry.get("category", ""),
            "tool_count": len(tools),
        }

    def carry_on_offers(self, get_session: Callable[[str], Any]) -> None:
        """Wakes each conversation whose offered connector is connected now, wherever the person
        connected it, once; the note is a turn of its own after any turn in progress."""
        log = OfferLog(self._settings.state_dir)
        for thread_id, name in log.waiting(self._connections):
            log.mark(thread_id, name, "connected")
            title = (catalog_entry(name) or {}).get("title", name)
            get_session(thread_id).tell(f"connector:{name}", connected_note(title))
