# ruff: noqa: E402
"""Web tests: a turn keeps running when the person leaves its conversation (switching to another
one closes the socket), and what it finished is there when they come back."""

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from .helpers import FakeToolCallingChatModel, _client_lg, _receive_until, _tool_call


class GatedModel(FakeToolCallingChatModel):
    """Answers only once the test lets it, so the test can leave the conversation mid-turn."""

    started: Any = None
    go: Any = None

    def _stream(self, *args: Any, **kwargs: Any) -> Any:
        self.started.set()
        assert self.go.wait(20)
        yield from super()._stream(*args, **kwargs)


def _history_text(client: Any, thread: str) -> str:
    with client.websocket_connect(f"/ws/{thread}") as ws:
        ws.receive_json()  # state
        return json.dumps(ws.receive_json(), ensure_ascii=False)


def test_a_turn_finishes_after_the_person_leaves_its_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = GatedModel(
        responses=[AIMessage(content="the report is written")],
        started=threading.Event(),
        go=threading.Event(),
    )
    with _client_lg(tmp_path, monkeypatch, model) as client:
        with client.websocket_connect("/ws/t_leave") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write the report"})
            assert model.started.wait(10)
        # The socket is closed here, as when the person opens another conversation.
        model.go.set()

        deadline = time.monotonic() + 15
        while "the report is written" not in _history_text(client, "t_leave"):
            assert time.monotonic() < deadline, "the turn did not finish after the socket closed"
            time.sleep(0.3)


def test_a_turn_that_reaches_an_approval_after_the_person_left_waits_for_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    model = GatedModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="written")],
        started=threading.Event(),
        go=threading.Event(),
    )
    with _client_lg(tmp_path, monkeypatch, model) as client:
        with client.websocket_connect("/ws/t_leave_ask") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            assert model.started.wait(10)
        model.go.set()
        time.sleep(1.5)  # the turn runs on, reaches the approval and parks there
        assert not (tmp_path / "workspace" / "note.txt").exists()

        with client.websocket_connect("/ws/t_leave_ask") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            redelivered = ws.receive_json()
            assert redelivered["type"] == "approval_required"
            ws.send_json({"type": "approval_response", "id": redelivered["id"], "approved": True})
            while ws.receive_json()["type"] != "tasks_changed":
                pass
    assert (tmp_path / "workspace" / "note.txt").read_text() == "hi"


def test_the_reply_of_a_turn_still_running_reaches_the_tab_that_came_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = GatedModel(
        responses=[AIMessage(content="the report is written")],
        started=threading.Event(),
        go=threading.Event(),
    )
    with _client_lg(tmp_path, monkeypatch, model) as client:
        with client.websocket_connect("/ws/t_back") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write the report"})
            assert model.started.wait(10)

        with client.websocket_connect("/ws/t_back") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            model.go.set()
            reply = _receive_until(ws, "agent_message")[-1]

    assert "the report is written" in reply["text"]
