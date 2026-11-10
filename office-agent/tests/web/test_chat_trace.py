# ruff: noqa: E402
"""Web tests: a turn through the chat socket leaves its line in the turn record."""

import json
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from coscribe.conversation.turn_record import turns_path

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


def test_a_turn_with_a_tool_call_is_recorded_without_its_words(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "read_file", {"path": "missing-budget.txt"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="There is no such file."),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_trace") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "what does the budget say"})
            _receive_until(ws, "tasks_changed")

    written = turns_path(tmp_path / "state").read_text(encoding="utf-8")
    [entry] = [json.loads(line) for line in written.splitlines()]
    assert entry["thread_id"] == "t_trace"
    assert entry["outcome"] == "completed"
    assert entry["notice"] is False
    assert entry["mode"] == "manual"
    assert entry["model_calls"] == 2
    assert entry["tools"]["read_file"]["calls"] == 1
    assert "what does the budget say" not in written
    assert "There is no such file." not in written


def test_a_stopped_turn_is_recorded_as_stopped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_trace_stop") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            assert ws.receive_json()["type"] == "approval_required"
            ws.send_json({"type": "stop"})
            _receive_until(ws, "tasks_changed")

    written = turns_path(tmp_path / "state").read_text(encoding="utf-8")
    [entry] = [json.loads(line) for line in written.splitlines()]
    assert entry["outcome"] == "stopped"


def test_a_command_that_runs_no_model_leaves_no_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="unused")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_trace_cmd") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/plan"})
            assert ws.receive_json()["type"] == "state"

    assert not turns_path(tmp_path / "state").exists()
