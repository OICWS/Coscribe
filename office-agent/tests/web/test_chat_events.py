# ruff: noqa: E402
"""Web tests: what the tab is told while a call runs, and after a reconnect."""

import json
import time
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
)
from langchain_core.outputs import ChatGenerationChunk

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _create_workflow_task,
    _receive_until,
    _structured,
    _tool_call,
    _wait_for_run_status,
    _wait_until,
)


def test_reconnect_replays_a_sent_images_data_urls_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real, user-reported bug: an attached image rendered fine for the
    rest of the live WS connection that sent it (the browser's own
    optimistic local echo, still holding the data URL in memory), but
    vanished on reload/reconnect/thread-switch-and-back -- the image was
    already faithfully checkpointed (baked into the HumanMessage's own
    image_url content blocks), just never read back out by
    serialize_history_for_ws_lg. See messages.py's extract_images and
    this same function's docstring."""
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="nice photo")])
    data_url = "data:image/png;base64,aGVsbG8="
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_hist_images") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history -- empty, brand new thread
            ws.send_json({"type": "user_message", "text": "what's in this?", "images": [data_url]})
            _receive_until(ws, "tasks_changed")

        with client.websocket_connect("/ws/t_hist_images") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert history == {
        "type": "history",
        "entries": [
            {"kind": "user", "text": "what's in this?", "images": [data_url]},
            {"kind": "agent", "text": "nice photo"},
        ],
        "has_older": False,
    }


def test_a_message_that_starts_an_artifact_keeps_the_note_out_of_the_replayed_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="on it")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_artifact") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history -- empty, brand new thread
            ws.send_json({"type": "user_message", "text": "a deck about tea", "artifact": "slides"})
            _receive_until(ws, "tasks_changed")

        with client.websocket_connect("/ws/t_artifact") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert history["entries"][0] == {"kind": "user", "text": "a deck about tea"}


class _SlowSecondReplyModel(FakeToolCallingChatModel):
    """The second reply takes a while, so a test can open and close a tab
    while that turn is still going."""

    slow_started: list[bool] = []

    def _stream(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> Any:
        if self.i == 1:
            self.slow_started.append(True)
            time.sleep(1.0)
        yield from super()._stream(messages, stop, run_manager, **kwargs)


def test_closing_a_tab_on_a_run_being_looked_into_leaves_it_going_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "notes.txt").write_text("one two", encoding="utf-8")
    fake_model = _SlowSecondReplyModel(
        responses=[_structured({"words": 0}), AIMessage(content="The file was empty.")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        task = _create_workflow_task(client)
        run = client.post(f"/api/scheduled-tasks/{task['trigger_id']}/run", json={}).json()["run"]
        _wait_for_run_status(client, task["trigger_id"], run["run_id"])
        base = f"/api/scheduled-tasks/{task['trigger_id']}/runs/{run['run_id']}"
        thread_id = client.post(f"{base}/investigate", json={}).json()["thread_id"]
        _wait_until(lambda: fake_model.slow_started)
        # A tab opens the conversation mid-turn and is closed again.
        with client.websocket_connect(f"/ws/{thread_id}") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
        # Waits on the turn's own end, not a fixed time: under a loaded CI
        # runner the rest of the turn can take longer than the slow reply.
        _wait_until(
            lambda: client.get("/api/threads/status").json()["statuses"][thread_id] != "working"
        )
        with client.websocket_connect(f"/ws/{thread_id}") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()["entries"]

    assert any(e.get("text") == "The file was empty." for e in history), history


def test_a_tool_call_is_announced_before_it_runs_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "list_files", {"path": "."})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_tool_started") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "list files"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    started = messages[types.index("tool_started")]
    assert started["tool_name"] == "list_files"
    assert started["arguments"] == {"path": "."}
    assert types.index("tool_started") < types.index("tool_result")


def test_a_call_waiting_for_approval_is_shown_only_as_its_approval_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_tool_started_gated") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write it"})
            before = _receive_until(ws, "approval_required")
            ws.send_json({"type": "approval_response", "id": before[-1]["id"], "approved": True})
            after = _receive_until(ws, "tasks_changed")

    assert not any(m["type"] == "tool_started" for m in before + after)


def test_an_auto_approved_call_is_announced_before_it_runs_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_tool_started_auto") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/accept-edits"})
            ws.receive_json()  # state
            ws.send_json({"type": "user_message", "text": "write it"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    assert types.index("tool_started") < types.index("tool_result")
    assert messages[types.index("tool_started")]["tool_name"] == "write_file"


class _IndexedToolCallModel(FakeToolCallingChatModel):
    """Streams tool calls the way real providers do: numbered from index 0
    in every response, the arguments split across chunks where only the
    first carries the call's id and name."""

    def _stream(self, messages: list[BaseMessage], *args: Any, **kwargs: Any) -> Any:
        self.received.append(list(messages))
        message = self.responses[self.i]
        self.i += 1
        yield ChatGenerationChunk(message=AIMessageChunk(content=message.content or ""))
        for index, call in enumerate(message.tool_calls):
            text = json.dumps(call["args"])
            half = len(text) // 2
            for piece, first in ((text[:half], True), (text[half:], False)):
                chunk = {
                    "name": call["name"] if first else None,
                    "args": piece,
                    "id": call["id"] if first else None,
                    "index": index,
                }
                yield ChatGenerationChunk(
                    message=AIMessageChunk(content="", tool_call_chunks=[chunk])  # type: ignore[list-item]
                )


def test_each_tool_result_carries_its_own_arguments_across_responses_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    (tmp_path / "workspace" / "a.txt").write_text("A", encoding="utf-8")
    (tmp_path / "workspace" / "b.txt").write_text("B", encoding="utf-8")
    fake_model = _IndexedToolCallModel(
        responses=[
            AIMessage(content="", tool_calls=[_tool_call("c1", "read_file", {"path": "a.txt"})]),
            AIMessage(content="", tool_calls=[_tool_call("c2", "read_file", {"path": "b.txt"})]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_two_reads") as ws:
            ws.receive_json()
            ws.receive_json()
            ws.send_json({"type": "user_message", "text": "read a then b"})
            messages = _receive_until(ws, "tasks_changed")

    results = [m["arguments"] for m in messages if m["type"] == "tool_result"]
    assert results == [{"path": "a.txt"}, {"path": "b.txt"}]


def test_a_slides_conversation_started_with_a_design_system_gets_it_and_its_deck_a_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="on it")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        made = client.post("/api/design-systems", json={"name": "Acme"}).json()
        client.put(
            f"/api/design-systems/{made['id']}",
            json={**made, "colors": [{"name": "Brand", "value": "#112233", "note": ""}]},
        )
        with client.websocket_connect("/ws/t_design") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json(
                {
                    "type": "user_message",
                    "text": "a deck about tea",
                    "artifact": "slides",
                    "design_system": made["id"],
                }
            )
            _receive_until(ws, "tasks_changed")
        sent = str(fake_model.received[0][-1].content)
        # Changing the library afterwards does not move what the conversation was told.
        client.put(f"/api/design-systems/{made['id']}", json={**made, "name": "Renamed"})
    assert 'Follow their design system "Acme".' in sent and "Brand #112233" in sent
    from coscribe.tools import DesignSystemStore

    kept = DesignSystemStore(tmp_path / "state").chosen_for_thread("t_design")
    assert kept is not None and kept["name"] == "Acme"


def test_a_design_system_that_is_not_in_the_library_or_not_for_slides_is_left_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="ok")] * 2)
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        made = client.post("/api/design-systems", json={"name": "Acme"}).json()
        with client.websocket_connect("/ws/t_nodesign") as ws:
            ws.receive_json()
            ws.receive_json()
            ws.send_json(
                {
                    "type": "user_message",
                    "text": "x",
                    "artifact": "slides",
                    "design_system": "aaaaaaaaaa",
                }
            )
            _receive_until(ws, "tasks_changed")
        with client.websocket_connect("/ws/t_docs") as ws:
            ws.receive_json()
            ws.receive_json()
            ws.send_json(
                {
                    "type": "user_message",
                    "text": "y",
                    "artifact": "docs",
                    "design_system": made["id"],
                }
            )
            _receive_until(ws, "tasks_changed")
    assert "design system" not in str(fake_model.received[0][-1].content)
    assert "design system" not in str(fake_model.received[1][-1].content)
