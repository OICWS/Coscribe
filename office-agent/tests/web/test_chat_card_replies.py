# ruff: noqa: E402
"""Web tests: words written in the chat while a question or an approval card waits answer it."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage, ToolMessage

from coscribe.runtime_lg import AuditLog

from .helpers import FakeToolCallingChatModel, _client_lg, _receive_until, _tool_call


def test_a_reply_written_instead_of_choosing_is_the_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call(
        "call_1",
        "ask_user_question",
        {"questions": [{"question": "Which one?", "options": [{"label": "A"}, {"label": "B"}]}]},
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_reply_q") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "ask me something"})
            question = ws.receive_json()
            reply = {"type": "question_response", "id": question["id"], "reply": "neither, use C"}
            ws.send_json(reply)
            _receive_until(ws, "tasks_changed")

    result = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)][-1]
    assert "didn't pick an option" in str(result.content)
    assert str(result.content).endswith("neither, use C")


def test_a_reply_written_instead_of_approving_denies_the_call_with_those_words(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="ok")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_reply_a") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            words = "name it hello.txt instead"
            ws.send_json(
                {
                    "type": "approval_response",
                    "id": approval["id"],
                    "approved": False,
                    "reply": words,
                }
            )
            _receive_until(ws, "tasks_changed")

    assert not (tmp_path / "workspace" / "note.txt").exists()
    result = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)][-1]
    assert "didn't approve this call" in str(result.content)
    assert str(result.content).endswith(words)
    [entry] = AuditLog(tmp_path / "state").read_all()
    assert entry.decision == "reject"
