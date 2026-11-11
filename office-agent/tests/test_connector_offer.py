"""The connector offer tools (decision 0046) and the catalog they search."""

import json
from pathlib import Path
from typing import Any

from coscribe.config import Settings
from coscribe.conversation.connector_offer import (
    OfferLog,
    build_connector_offer_tools,
    connected_note,
)
from coscribe.web.connector_directory import CatalogDirectory


class _Directory:
    def __init__(self, state: str = "available") -> None:
        self.state = state

    def search(self, need: str, limit: int) -> list[dict[str, Any]]:
        return [{"name": "notion", "title": "Notion", "description": "", "state": self.state}]

    def card(self, name: str) -> dict[str, Any] | None:
        if name != "notion":
            return None
        return {"name": "notion", "title": "Notion", "description": "d", "state": self.state}


def _tools(tmp_path: Path, directory: Any = None, run: bool = False) -> tuple[Any, Any]:
    found, offer = build_connector_offer_tools(
        directory or _Directory(), tmp_path, "t1", lambda: run
    )
    return found, offer


def test_an_offer_returns_the_card_and_is_remembered_for_the_conversation(tmp_path: Path) -> None:
    _, offer = _tools(tmp_path)
    result = offer("notion", "  To read your page.  ")
    assert result["status"] == "offered"
    assert result["title"] == "Notion"
    assert result["why"] == "To read your page."
    assert OfferLog(tmp_path).state("t1", "notion") == "offered"


def test_a_declined_connector_is_not_offered_again_in_that_conversation(tmp_path: Path) -> None:
    _, offer = _tools(tmp_path)
    OfferLog(tmp_path).mark("t1", "notion", "declined")
    assert offer("notion", "why")["status"] == "declined"
    _, elsewhere = build_connector_offer_tools(_Directory(), tmp_path, "t2", lambda: False)
    assert elsewhere("notion", "why")["status"] == "offered"


def test_no_card_for_an_unknown_connector_a_connected_one_or_a_workflow_run(tmp_path: Path) -> None:
    _, offer = _tools(tmp_path)
    assert offer("notion-ish", "why")["status"] == "refused"
    _, connected = _tools(tmp_path, _Directory("connected"))
    assert connected("notion", "why")["status"] == "connected"
    _, in_run = _tools(tmp_path, run=True)
    assert in_run("notion", "why")["status"] == "refused"
    assert OfferLog(tmp_path).state("t1", "notion") is None


def test_forgetting_a_conversation_drops_only_its_offers(tmp_path: Path) -> None:
    log = OfferLog(tmp_path)
    log.mark("t1", "notion", "declined")
    log.mark("t2", "notion", "offered")
    log.forget("t1")
    assert log.state("t1", "notion") is None
    assert log.state("t2", "notion") == "offered"


def test_the_connected_note_names_the_connector() -> None:
    assert connected_note("Notion").startswith("[Connector connected] The user connected Notion")


class _OAuth:
    def __init__(self, apps: set[str]) -> None:
        self.apps = apps

    def app(self, group: str) -> tuple[str, None] | None:
        return ("id", None) if group in self.apps else None


def _directory(tmp_path: Path, servers: dict[str, Any], live: set[str], apps: set[str]) -> Any:
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None, default_model="openai:x", state_dir=tmp_path, mcp_config_path=config
    )
    return CatalogDirectory(settings, dict.fromkeys(live), _OAuth(apps))  # type: ignore[arg-type]


def test_the_catalog_search_puts_the_named_service_first(tmp_path: Path) -> None:
    directory = _directory(tmp_path, {}, set(), set())
    assert directory.search("Notion pages", 3)[0]["name"] == "notion"
    assert directory.search("Jira issues", 3)[0]["name"] == "atlassian"
    assert directory.search("the of my", 3) == []
    assert len(directory.search("search", 3)) <= 3


def test_each_connector_state_comes_from_the_live_connections_and_saved_config(
    tmp_path: Path,
) -> None:
    servers = {"notion": {"server_url": "https://mcp.notion.com/mcp", "auth": "oauth"}}
    directory = _directory(tmp_path, servers, {"canva"}, set())
    assert directory.card("canva")["state"] == "connected"
    assert directory.card("notion")["state"] == "signed_out"
    assert directory.card("hubspot")["state"] == "needs_setup"
    assert directory.card("atlassian")["state"] == "available"
    assert directory.card("nope") is None
    assert directory.card("notion")["tool_count"] > 0
