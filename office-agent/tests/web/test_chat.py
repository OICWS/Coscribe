# ruff: noqa: E402
"""Web tests: the chat turn: streaming, usage, notes and the first approval."""

import json
import time
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)
from langchain_core.messages.ai import UsageMetadata

from coscribe.conversation import ThreadMetaStore
from coscribe.runtime_lg.audit import AuditLog
from coscribe.runtime_lg.messages import is_steer

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


def test_chat_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t1") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history
            assert state["type"] == "state"
            assert state["plan_mode"] is False
            assert state["accept_edits"] is False
            assert state["model"] == "fake:model"
            assert isinstance(state["context_window"], int)

            ws.send_json({"type": "user_message", "text": "hello"})
            messages = _receive_until(ws, "tasks_changed")

    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "hi there!"
    assert messages[-1]["type"] == "tasks_changed"


def test_usage_event_sent_when_the_model_reports_usage_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a real, live-reported gap: the WS "usage" event
    (drives the frontend's context-usage bar) was deliberately never sent,
    because an earlier check against streaming Gemini found
    AIMessageChunk.usage_metadata always came back all zeros. Re-checked
    live against the currently pinned langchain-google-genai and found that
    finding stale -- an upstream fix means real per-chunk usage now flows
    through this exact astream(stream_mode=["messages"]) path. See
    runtime_lg/README.md's "usage bar" section for the live verification
    (including a real tool call and a second turn's usage correctly
    growing) this unit test can't reach on its own (FakeToolCallingChatModel
    has no live API to hit)."""
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="hi there!",
                usage_metadata=UsageMetadata(input_tokens=10, output_tokens=5, total_tokens=15),
            )
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_usage") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            messages = _receive_until(ws, "tasks_changed")

    usage_message = next(m for m in messages if m["type"] == "usage")
    assert usage_message == {"type": "usage", "total_tokens": 15}


def test_usage_events_are_live_per_response_not_summed_across_a_tool_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tool-calling turn involves two separate model responses (propose
    the call, then respond to its result) -- each one's own usage_metadata
    already reflects the *cumulative* context size at that point (every
    provider reports "tokens in the whole prompt this call sent" as
    input_tokens, not a delta since the last call), so summing both
    responses together would double-count: the sequence below must never
    contain 145 (60 + 85).

    Also the live-per-segment regression test for RunStatus's running
    turn timer: _stream_turn sends "usage" itself at each ToolMessage
    boundary now, not only once the whole turn is over, so the first
    response's total (60) must reach the client *before* that call's own
    "tool_result" event -- proof it's live, not batched to the end. The
    final 85 shows up twice (once from _stream_turn's own end-of-call
    send, once more from this handler's existing post-turn send) --
    harmless, same value both times, not worth suppressing the second
    one for."""
    call = _tool_call("call_1", "list_files", {})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[call],
                usage_metadata=UsageMetadata(input_tokens=50, output_tokens=10, total_tokens=60),
            ),
            AIMessage(
                content="done",
                usage_metadata=UsageMetadata(input_tokens=80, output_tokens=5, total_tokens=85),
            ),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_usage_tool") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "list files"})
            messages = _receive_until(ws, "tasks_changed")

    usage_totals = [m["total_tokens"] for m in messages if m["type"] == "usage"]
    assert usage_totals == [60, 85, 85]

    usage_60 = {"type": "usage", "total_tokens": 60}
    usage_60_index = next(i for i, m in enumerate(messages) if m == usage_60)
    tool_result_index = next(i for i, m in enumerate(messages) if m["type"] == "tool_result")
    assert usage_60_index < tool_result_index


def test_no_usage_event_when_the_model_never_reports_usage_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_usage_none") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            messages = _receive_until(ws, "tasks_changed")

    assert not any(m["type"] == "usage" for m in messages)


def test_agent_delta_events_stream_before_the_final_agent_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t10") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "agent_delta" in types
    assert types.index("agent_delta") < types.index("agent_message")
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "hi there!"


def test_write_file_requires_approval_and_executes_when_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})

            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            assert approval["tool_name"] == "write_file"
            assert approval["arguments"] == {"path": "note.txt", "content": "hi"}

            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "tool_result" in types
    assert types.index("tool_result") < types.index("agent_message")
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "done"
    assert (tmp_path / "workspace" / "note.txt").read_text() == "hi"

    entries = AuditLog(tmp_path / "state").read_all()
    assert len(entries) == 1
    assert entries[0].thread_id == "t2"
    assert entries[0].tool_name == "write_file"
    assert entries[0].decision == "approve"
    assert entries[0].reason == "human"


def test_a_note_sent_mid_turn_reaches_the_model_at_its_next_step_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.runtime_lg.messages import STEER_NOTE

    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_steer1") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"

            ws.send_json({"type": "steer", "id": "s1", "text": "and make it a list"})
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            messages = _receive_until(ws, "tasks_changed")

    assert {"type": "steers_delivered", "ids": ["s1"]} in messages
    assert not any(m["type"] == "steers_requeued" for m in messages)
    last = fake_model.received[-1][-1]
    assert isinstance(last, HumanMessage)
    assert last.content == STEER_NOTE + "and make it a list"
    assert next(m for m in messages if m["type"] == "agent_message")["text"] == "done"


def test_a_note_no_turn_was_left_to_read_is_sent_as_the_next_message_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="noted")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_steer2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "steer", "id": "s1", "text": "one more thing"})
            requeued = ws.receive_json()
            messages = _receive_until(ws, "tasks_changed")

    assert requeued == {"type": "steers_requeued", "ids": ["s1"], "text": "one more thing"}
    sent = fake_model.received[-1][-1]
    assert isinstance(sent, HumanMessage) and "one more thing" in str(sent.content)
    assert not is_steer(sent)
    assert next(m for m in messages if m["type"] == "agent_message")["text"] == "noted"


def test_stop_drops_the_notes_the_model_has_not_read_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="", tool_calls=[call])])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_steer3") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            assert ws.receive_json()["type"] == "approval_required"
            ws.send_json({"type": "steer", "id": "s1", "text": "never mind the list"})
            ws.send_json({"type": "stop"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "steers_requeued" not in types and "steers_delivered" not in types
    assert len(fake_model.received) == 1


def test_a_withdrawn_note_is_never_read_by_the_model_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_steer4") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            ws.send_json({"type": "steer", "id": "s1", "text": "and make it a list"})
            ws.send_json({"type": "steer", "id": "s1", "text": None})
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            messages = _receive_until(ws, "tasks_changed")

    assert not any(m["type"] in ("steers_delivered", "steers_requeued") for m in messages)
    assert "make it a list" not in str(fake_model.received[-1][-1].content)


def test_the_sidebar_status_follows_a_conversation_from_waiting_to_ready_to_seen_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/side1") as ws:
            ws.receive_json()
            ws.receive_json()
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            waiting = client.get("/api/threads/status").json()["statuses"]["side1"]
            listed = {t["thread_id"]: t for t in client.get("/api/threads").json()}

            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")
            for _ in range(40):  # the turn lock is released just after the event
                watched = client.get("/api/threads/status").json()["statuses"]["side1"]
                if watched != "working":
                    break
                time.sleep(0.05)

        # The tab closed; a turn that ends now has nobody looking.
        unseen = ThreadMetaStore(tmp_path / "state")
        unseen.mark_finished("side1", watched=False)
        ready = client.get("/api/threads/status").json()["statuses"]["side1"]
        with client.websocket_connect("/ws/side1") as ws:
            ws.receive_json()
            seen = client.get("/api/threads/status").json()["statuses"]["side1"]

    assert waiting == "needs_input"
    assert listed["side1"]["status"] == "needs_input"
    assert watched == "idle"
    assert ready == "ready"
    assert seen == "idle"


def test_narration_before_a_gated_tool_call_does_not_get_glued_onto_the_final_reply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real bug, found live against DeepSeek/GLM (both narrate before a
    gated tool call, unlike Gemini/Anthropic in this app's usual testing):
    the pre-tool narration text streamed live as its own "agent_delta" run,
    then got concatenated with no separator onto the *front* of the final
    "agent_message" -- "I'll write it now.Done, I wrote the file." glued
    together, because session.py's turn handler used to join every model
    response of a turn into one string. Fixed by having _stream_turn/
    _resolve_pending_approvals each return only their own *last* response's
    text -- see their docstrings."""
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="I'll write it now.", tool_calls=[call]),
            AIMessage(content="Done, I wrote the file."),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t2b") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})

            delta = ws.receive_json()
            assert delta == {"type": "agent_delta", "text": "I'll write it now."}
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"

            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            messages = _receive_until(ws, "tasks_changed")

    deltas = [m["text"] for m in messages if m["type"] == "agent_delta"]
    assert deltas == ["Done, I wrote the file."]
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    # The bug's exact shape: "I'll write it now.Done, I wrote the file."
    assert agent_message["text"] == "Done, I wrote the file."


def test_narration_before_an_ungated_tool_call_does_not_get_glued_onto_the_final_reply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same underlying bug as
    test_narration_before_a_gated_tool_call_does_not_get_glued_onto_the_
    final_reply, but for a tool that never asks for approval -- both
    model responses stream within a *single* _stream_turn call here (no
    approval_required event splits them), so this exercises that
    method's own text_parts.clear() reset at the ToolMessage boundary,
    not _resolve_pending_approvals's fix."""
    call = _tool_call("call_1", "read_file", {"path": "note.txt"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="Let me check that file.", tool_calls=[call]),
            AIMessage(content="It says hello."),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_ungated_narration") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
            (tmp_path / "workspace" / "note.txt").write_text("hello")
            ws.send_json({"type": "user_message", "text": "read note.txt"})
            messages = _receive_until(ws, "tasks_changed")

    deltas = [m["text"] for m in messages if m["type"] == "agent_delta"]
    assert deltas == ["Let me check that file.", "It says hello."]
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    # The bug's exact shape: "Let me check that file.It says hello."
    assert agent_message["text"] == "It says hello."


def test_edit_file_batch_tool_works_end_to_end_through_the_agent_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real, live verification that edit_file_batch's `edits` string
    argument round-trips correctly through the actual LangGraph/
    LangChain tool-schema machinery (build_langgraph_agent -> a real
    StructuredTool, not just this function called directly in Python
    the way test_files_tool.py's unit tests do)."""
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    (tmp_path / "workspace" / "a.txt").write_text("hello world\nsecond line\n", encoding="utf-8")
    call = _tool_call(
        "call_1",
        "edit_file_batch",
        {
            "path": "a.txt",
            "edits": "world\n---\nthere\n---\nsecond line\n---\nSECOND LINE",
        },
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_batch_edit") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "make both edits"})

            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            assert approval["tool_name"] == "edit_file_batch"
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            messages = _receive_until(ws, "tasks_changed")

    tool_result = next(m for m in messages if m["type"] == "tool_result")
    assert "2" in json.dumps(tool_result)  # edits_applied
    assert (tmp_path / "workspace" / "a.txt").read_text() == "hello there\nSECOND LINE\n"
