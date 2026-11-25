# ruff: noqa: E402
"""Web tests: the model asking the user a question, and redelivery after a reconnect."""

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
    ToolMessage,
)

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)

_CARD = {
    "questions": [
        {
            "question": "Who is the deck for?",
            "options": [
                {"label": "Management", "description": "8 slides", "recommended": True},
                {"label": "Team"},
            ],
        }
    ]
}


def _connect(ws: Any) -> None:
    ws.receive_json()  # state
    ws.receive_json()  # history


def test_a_question_shows_its_card_and_lets_the_turn_go_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_tool_call("call_1", "ask_user_question", _CARD)]),
            AIMessage(content="I'll wait for your answer."),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q1") as ws:
            _connect(ws)
            ws.send_json({"type": "user_message", "text": "make a deck from the sales data"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "question_required" not in types
    assert "approval_required" not in types
    shown = next(m for m in messages if m["type"] == "tool_result")
    assert shown["tool_name"] == "ask_user_question"
    assert shown["arguments"] == _CARD
    assert "on a card in the conversation" in str(shown["result"])
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "I'll wait for your answer."


def test_a_question_is_not_blocked_by_plan_mode_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_tool_call("call_1", "ask_user_question", _CARD)]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q3") as ws:
            _connect(ws)
            ws.send_json({"type": "user_message", "text": "/plan"})
            ws.receive_json()  # state (plan_mode: True)
            ws.send_json({"type": "user_message", "text": "ask me something"})
            messages = _receive_until(ws, "tasks_changed")

    shown = next(m for m in messages if m["type"] == "tool_result")
    assert "on a card in the conversation" in str(shown["result"])


def _note_in(message: Any) -> bool:
    return "[Open question card]" in str(message.content)


def test_the_next_message_tells_the_model_a_card_is_open_until_it_is_answered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ask = _tool_call("call_1", "ask_user_question", _CARD)
    answered = _tool_call("call_2", "answer_question_card", {"answers": ["Management"]})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[ask]),
            AIMessage(content="waiting"),
            AIMessage(content="It's 3 pm."),
            AIMessage(content="", tool_calls=[answered]),
            AIMessage(content="Management it is."),
            AIMessage(content="ok"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q_note") as ws:
            _connect(ws)
            for text in ("make a deck", "what time is it?", "for my boss", "thanks"):
                ws.send_json({"type": "user_message", "text": text})
                messages = _receive_until(ws, "tasks_changed")
                last_user = [m for m in fake_model.received[-1] if m.type == "human"][-1]
                assert _note_in(last_user) is (text in ("what time is it?", "for my boss"))
        with client.websocket_connect("/ws/t_q_note") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert "Who is the deck for?" in str(fake_model.received[2][-1].content)
    recorded = next(m for m in messages if m["type"] == "agent_message")
    assert recorded["text"] == "ok"
    shown = json.dumps(history)
    assert "[Open question card]" not in shown


def test_a_click_on_the_card_is_the_answer_and_carries_no_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_tool_call("call_1", "ask_user_question", _CARD)]),
            AIMessage(content="waiting"),
            AIMessage(content="Management it is."),
            AIMessage(content="ok"),
        ]
    )
    click = "[Answers to your question card]\n1. Who is the deck for? -> Management"
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q_click") as ws:
            _connect(ws)
            for text in ("make a deck", click, "thanks"):
                ws.send_json({"type": "user_message", "text": text})
                _receive_until(ws, "tasks_changed")
                last_user = [m for m in fake_model.received[-1] if m.type == "human"][-1]
                assert not _note_in(last_user)


def test_answer_question_card_needs_every_answer() -> None:
    from coscribe.tools.bookkeeping.interaction import answer_question_card

    assert "closed" in answer_question_card(["Management", "Brand"])
    for partial in ([], ["Management", " "]):
        with pytest.raises(ValueError, match="Every question needs an answer"):
            answer_question_card(partial)


def test_a_click_behind_a_note_about_edits_in_the_app_still_answers_the_card() -> None:
    from langchain_core.messages import HumanMessage

    from coscribe.conversation.turn_text import OPEN_QUESTION_NOTE, open_question
    from coscribe.runtime_lg import strip_mode_note

    ask = AIMessage(content="", tool_calls=[_tool_call("call_1", "ask_user_question", _CARD)])
    shown = ToolMessage(content="shown", tool_call_id="call_1", name="ask_user_question")
    edits = "The user edited slide 2 of deck.pptx since your last turn.\n\n"
    click = edits + "[Answers to your question card]\n1. Who is the deck for? -> Team"
    note = OPEN_QUESTION_NOTE.format(questions="- Who is the deck for?")

    assert open_question([ask, shown]) == ["Who is the deck for?"]
    assert open_question([ask, shown, HumanMessage(content=click)]) == []
    assert strip_mode_note(note + edits + "hello") == edits + "hello"


def test_a_failed_question_call_opens_no_card() -> None:
    from coscribe.conversation.turn_text import open_question

    ask = AIMessage(content="", tool_calls=[_tool_call("call_1", "ask_user_question", _CARD)])
    failed = ToolMessage(
        content="bad arguments", tool_call_id="call_1", name="ask_user_question", status="error"
    )

    assert open_question([ask, failed]) == []


def test_pending_approval_is_redelivered_on_reconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The checkpointer-backed regression test for cli_lg.py's real
    # process-restart test (see runtime_lg/README.md) -- here, within one
    # process, connect once, trigger an approval, disconnect *without*
    # responding, then reconnect a fresh WebSocket to the same thread_id and
    # confirm the still-pending approval is redelivered rather than lost.
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t2b") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            first_approval = ws.receive_json()
            assert first_approval["type"] == "approval_required"
        # disconnected without ever sending approval_response

        assert not (tmp_path / "workspace" / "note.txt").exists()

        with client.websocket_connect("/ws/t2b") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            redelivered = ws.receive_json()
            assert redelivered["type"] == "approval_required"
            assert redelivered["tool_name"] == "write_file"

            ws.send_json({"type": "approval_response", "id": redelivered["id"], "approved": True})
            messages = _receive_until(ws, "tasks_changed")

    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "done"
    assert (tmp_path / "workspace" / "note.txt").read_text() == "hi"


def test_a_pending_question_is_redelivered_every_time_the_conversation_is_reopened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Leaving a conversation and coming back again and again, never answering:
    # a redelivered question that outlives its connection must not keep the
    # turn lock, or the next reconnect finds nothing to answer.
    call = _tool_call("call_1", "remember", {"line": "Write in English."})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q_again") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "plan"})
            assert ws.receive_json()["type"] == "question_required"

        for _ in range(3):
            with client.websocket_connect("/ws/t_q_again") as ws:
                ws.receive_json()  # state
                ws.receive_json()  # history
                assert ws.receive_json()["type"] == "question_required"

        with client.websocket_connect("/ws/t_q_again") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            question = ws.receive_json()
            ws.send_json(
                {"type": "question_response", "id": question["id"], "answers": ["Don't save"]}
            )
            messages = _receive_until(ws, "tasks_changed")

    assert next(m for m in messages if m["type"] == "agent_message")["text"] == "done"


@pytest.mark.parametrize("answer", ["Save everywhere", "Save for this folder", "Don't save"])
def test_remember_writes_the_line_only_when_the_user_saves_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    line = "Use Templates/brand.pptx for every deck."
    call = _tool_call("call_1", "remember", {"line": line})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    memory = tmp_path / "MEMORY.md"
    memory.write_text("- Write in English.\n", encoding="utf-8")
    with _client_lg(tmp_path, monkeypatch, fake_model, memory_path=memory) as client:
        with client.websocket_connect("/ws/t_remember") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "always use our brand template"})
            question = ws.receive_json()
            assert question["type"] == "question_required"
            assert line in question["questions"][0]["question"]
            ws.send_json({"type": "question_response", "id": question["id"], "answers": [answer]})
            _receive_until(ws, "tasks_changed")

    tool_messages = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    folder_notes = tmp_path / "workspace" / ".coscribe" / "memory.md"
    if answer == "Save everywhere":
        assert memory.read_text(encoding="utf-8") == f"- Write in English.\n- {line}\n"
        assert "Saved" in str(tool_messages[-1].content)
    elif answer == "Save for this folder":
        assert memory.read_text(encoding="utf-8") == "- Write in English.\n"
        assert folder_notes.read_text(encoding="utf-8") == f"- {line}\n"
        assert "Saved to the notes" in str(tool_messages[-1].content)
    else:
        assert memory.read_text(encoding="utf-8") == "- Write in English.\n"
        assert not folder_notes.exists()
        assert "didn't save" in str(tool_messages[-1].content)
