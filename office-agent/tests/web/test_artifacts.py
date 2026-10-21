# ruff: noqa: E402
"""Web tests: the Artifacts page's list."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from .helpers import FakeToolCallingChatModel, _client_lg, _run_turn, _tool_call


def _made(*paths: str) -> AIMessage:
    calls = [
        _tool_call(f"c{i}", "write_file", {"path": p, "content": "x"}) for i, p in enumerate(paths)
    ]
    return AIMessage(content="", tool_calls=calls)


def test_the_artifacts_route_lists_the_decks_documents_and_sheets_the_conversations_made_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    fake_model = FakeToolCallingChatModel(
        responses=[
            # A lock file Word leaves and a plain note are not artifacts.
            _made("deck.pptx", "report.docx", "numbers.xlsx", "notes.md", "~$report.docx"),
            AIMessage(content="done"),
            _made("later.docx"),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        assert client.get("/api/artifacts").json() == []  # no conversation has run
        _run_turn(client, "t_one", "make things")
        first = client.get("/api/artifacts").json()
        _run_turn(client, "t_two", "one more")
        (tmp_path / "workspace" / "deck.pptx").unlink()
        second = client.get("/api/artifacts").json()

    kinds = {a["name"]: (a["kind"], a["thread_id"]) for a in first}
    assert kinds == {
        "deck": ("slides", "t_one"),
        "report": ("docs", "t_one"),
        "numbers": ("sheets", "t_one"),
    }
    assert all(a["modified_at"] and a["path"].startswith(a["name"]) for a in first)
    # The new conversation's file is listed, and the deck taken from the disk is not.
    assert {a["name"] for a in second} == {"report", "numbers", "later"}
