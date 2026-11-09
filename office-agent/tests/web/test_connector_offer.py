# ruff: noqa: E402
"""A conversation offers a connector from the built-in catalog on a card (decision 0041)."""

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage, ToolMessage

from coscribe.conversation.connector_offer import (
    OFFER_KEY,
    TOOL_NAME,
    build_connector_offer_tools,
    matching_entries,
)
from coscribe.runtime import get_tool_metadata
from coscribe.runtime_lg import build_search_tools_tool

from .helpers import FakeToolCallingChatModel, _client_lg, _receive_until, _tool_call


def _entry(name: str, title: str, does: str, added: bool = False) -> dict[str, Any]:
    return {"name": name, "title": title, "description": does, "added": added}


_CATALOG = [
    _entry("notion", "Notion", "Search, read and edit your Notion workspace."),
    _entry("atlassian", "Atlassian", "Search and update Jira and Confluence."),
    _entry("gmail", "Gmail", "Read and draft email in your Gmail.", added=True),
    _entry("google-drive", "Google Drive", "Search and read files in your Google Drive."),
]


def _offer(thread_id: str = "t1") -> Any:
    (tool,) = build_connector_offer_tools(lambda: _CATALOG, thread_id)
    return tool


def test_a_search_finds_the_entries_not_added_that_fit_it() -> None:
    assert [e["name"] for e in matching_entries(_CATALOG, "jira issues")] == ["atlassian"]
    assert [e["name"] for e in matching_entries(_CATALOG, "notion page")] == ["notion"]
    # Added already, so its own tools answer; and words the built-in tools cover find nothing.
    assert matching_entries(_CATALOG, "gmail draft") == []
    assert matching_entries(_CATALOG, "read pdf files") == []


def test_the_offer_names_only_a_catalog_entry_once_and_never_in_a_run() -> None:
    offer = _offer()
    assert "Names: notion, atlassian, gmail, google-drive" in offer(
        {}, "c9", "https://evil.example", "x"
    )
    assert "already added" in offer({}, "c9", "gmail", "x")

    card = json.loads(offer({}, "c9", "Notion", "  To  add the notes\nto your page. "))
    assert card[OFFER_KEY] == "notion"
    assert card["reason"] == "To add the notes to your page."
    assert "End your turn" in card["next"]

    earlier = ToolMessage(content=json.dumps(card), tool_call_id="c1", name=TOOL_NAME)
    assert "already offered" in offer({"messages": [earlier]}, "c9", "notion", "again")
    # Two calls for one entry in the same reply: only the first gets a card.
    both = AIMessage(
        content="",
        tool_calls=[
            _tool_call(c, TOOL_NAME, {"name": "notion", "reason": "x"}) for c in ("a", "b")
        ],
    )
    assert OFFER_KEY in offer({"messages": [both]}, "a", "notion", "x")
    assert "already offered" in offer({"messages": [both]}, "b", "notion", "x")
    # With every tool bound there is no search_tools; a need instead of a name finds the entry.
    assert "Ones that fit: atlassian (Search and update Jira" in offer({}, "c9", "jira", "x")
    assert "Nobody can connect" in _offer("scheduled-t-r1")({}, "c9", "notion", "x")
    assert build_connector_offer_tools(None, "t1") == []


def test_search_tools_lists_what_the_offer_can_find() -> None:
    def read_notes(path: str) -> str:
        """Read a notes file."""
        return path

    search = build_search_tools_tool([read_notes, _offer()])
    found = json.loads(search("jira"))
    assert [r["name"] for r in found] == [TOOL_NAME]
    (atlassian,) = found[0]["found"]
    assert atlassian == {
        "name": "atlassian",
        "title": "Atlassian",
        "does": _CATALOG[1]["description"],
    }
    assert "state" not in found[0]["parameters"]["properties"]
    assert get_tool_metadata(_offer()).risk_category == "READ"
    assert [r["name"] for r in json.loads(search("read notes file"))] == ["read_notes"]


def test_a_conversation_offers_a_catalog_connector_and_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    calls = [
        _tool_call("c1", "suggest_connector", {"name": "notion", "reason": "To read the plan."}),
        _tool_call("c2", "suggest_connector", {"name": "canva", "reason": "To export."}),
    ]
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=calls), AIMessage(content="Connect Notion.")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        client.post(
            "/api/mcp/servers", json={"name": "canva", "server_url": "https://mcp.canva.com/mcp"}
        )
        with client.websocket_connect("/ws/offer") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "Summarize my Notion plan"})
            events = _receive_until(ws, "tasks_changed")
    # Two calls at once may finish in either order; the card reads the result alone.
    results = [e["result"] for e in events if e["type"] == "tool_result"]
    (card,) = [r for r in results if isinstance(r, dict)]
    assert card[OFFER_KEY] == "notion"
    assert any("Canva is already added" in r for r in results if isinstance(r, str))
