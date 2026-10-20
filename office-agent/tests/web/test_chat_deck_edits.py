# ruff: noqa: E402
"""Web tests: the user's slide edits are told to coscribe in front of the next message."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from coscribe.conversation import deck_edits

from .helpers import FakeToolCallingChatModel, _client_lg, _receive_until


def test_a_change_the_user_made_is_told_once_in_front_of_the_next_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "deck.pptx").write_bytes(b"")
    told = [{"folder": "deck-pages", "edited": ["02-cards.html"], "added": [], "removed": []}, None]
    monkeypatch.setattr(
        deck_edits,
        "summarize_activity",
        lambda *_: {"outputs": [{"path": "deck.pptx", "exists": True}], "references": []},
    )
    monkeypatch.setattr(deck_edits, "deck_edits_since_coscribe", lambda _deck: told.pop(0))
    model = FakeToolCallingChatModel(responses=[AIMessage(content="one"), AIMessage(content="two")])
    with _client_lg(tmp_path, monkeypatch, model) as client:
        with client.websocket_connect("/ws/t_deck_edits") as ws:
            ws.receive_json()
            ws.receive_json()
            for text in ("first", "second"):
                ws.send_json({"type": "user_message", "text": text})
                _receive_until(ws, "tasks_changed")

    first, second = (calls[-1].content for calls in model.received[:2])
    assert "The user changed the slides of deck.pptx in the app" in str(first)
    assert "edited 02-cards.html" in str(first) and str(first).rstrip().endswith("first")
    assert "The user changed the slides" not in str(second)
