# ruff: noqa: E402
"""Web tests: clearing, stopping, compaction, editing and the replayed history."""

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)

from coscribe.tools.office.document_tools import DocumentToolkit

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


def test_clear_wipes_conversation_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_clear") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")

            ws.send_json({"type": "user_message", "text": "/clear"})
            cleared = ws.receive_json()
            assert cleared == {"type": "cleared"}

            # Behavioral proof the history is really gone, not just that the
            # event fired -- /compact's own "nothing much to compact" guard
            # (< 4 messages) only trips on a genuinely empty thread.
            ws.send_json({"type": "user_message", "text": "/compact"})
            error = ws.receive_json()

    assert error["type"] == "error"
    assert "Nothing much to compact" in error["message"]


def test_stop_mid_tool_closes_the_orphaned_tool_call_instead_of_breaking_the_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stop hard-cancels a turn while a tool is still running: the
    checkpoint is left with an AIMessage whose tool_call never got a
    ToolMessage. The next message must reach the model with that call
    closed off (OpenAI-compatible providers 400 on the whole history
    otherwise), and reconnecting must not silently re-run the tool."""
    from langchain_core.messages import ToolCall

    started = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    def slow_search_pdf(self: Any, query: str, **kwargs: Any) -> list[dict[str, object]]:
        calls.append(query)
        started.set()
        release.wait(timeout=10)
        return []

    monkeypatch.setattr(DocumentToolkit, "search_pdf", slow_search_pdf)
    call = ToolCall(name="search_pdf", args={"query": "Error code"}, id="call_1")
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="hi")]
    )
    try:
        with _client_lg(tmp_path, monkeypatch, fake_model) as client:
            with client.websocket_connect("/ws/t_stop_mid_tool") as ws:
                ws.receive_json()  # state
                ws.receive_json()  # history
                ws.send_json({"type": "user_message", "text": "search the manual"})
                assert started.wait(timeout=5), "tool never started"
                ws.send_json({"type": "stop"})
                stopped = _receive_until(ws, "agent_message")[-1]
                assert stopped["text"] == "[stopped]"
                release.set()

            with client.websocket_connect("/ws/t_stop_mid_tool") as ws:
                ws.receive_json()  # state
                ws.receive_json()  # history
                ws.send_json({"type": "user_message", "text": "just say hi"})
                messages = _receive_until(ws, "tasks_changed")
    finally:
        release.set()

    assert calls == ["Error code"]
    assert not any(m["type"] == "error" for m in messages)
    assert [m for m in messages if m["type"] == "agent_message"][-1]["text"] == "hi"
    history = fake_model.received[-1]
    tool_call_index = next(
        i for i, m in enumerate(history) if isinstance(m, AIMessage) and m.tool_calls
    )
    closing = history[tool_call_index + 1]
    assert isinstance(closing, ToolMessage)
    assert closing.tool_call_id == "call_1"
    assert isinstance(history[tool_call_index + 2], HumanMessage)


def test_close_orphaned_tool_calls_heals_a_thread_already_corrupted_mid_history() -> None:
    """A thread broken before the fix has a newer HumanMessage *after*
    the orphaned tool call -- the placeholder has to be inserted directly
    after its AIMessage, not appended at the end."""
    from langchain.agents import create_agent
    from langchain_core.messages import ToolCall
    from langgraph.checkpoint.memory import InMemorySaver

    from coscribe.conversation.history import (
        close_orphaned_tool_calls as _close_orphaned_tool_calls,
    )

    def lookup(q: str) -> str:
        """Look something up."""
        return "found"

    calls = [
        ToolCall(name="lookup", args={"q": "a"}, id="done"),
        ToolCall(name="lookup", args={"q": "b"}, id="orphan"),
    ]
    agent = create_agent(
        FakeToolCallingChatModel(responses=[]), [lookup], checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": "t"}}

    async def scenario() -> list[BaseMessage]:
        await agent.aupdate_state(
            config,
            {
                "messages": [
                    HumanMessage(content="go"),
                    AIMessage(content="", tool_calls=calls),
                    ToolMessage(content="found", tool_call_id="done", name="lookup"),
                    HumanMessage(content="second"),
                ]
            },
            as_node="tools",
        )
        assert await _close_orphaned_tool_calls(agent, config) is True
        assert await _close_orphaned_tool_calls(agent, config) is False
        state = await agent.aget_state(config)
        assert state.next == ()
        return list(state.values["messages"])

    messages = asyncio.run(scenario())
    assert [type(m).__name__ for m in messages] == [
        "HumanMessage",
        "AIMessage",
        "ToolMessage",
        "ToolMessage",
        "HumanMessage",
    ]
    assert [m.tool_call_id for m in messages[2:4]] == ["done", "orphan"]


def test_compact_collapses_history_and_survives_a_later_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="hi there!"),
            AIMessage(content="nice to hear"),
            AIMessage(content="a short summary of the chat"),
            AIMessage(content="still here"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t4e") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "how are you"})
            _receive_until(ws, "tasks_changed")

            ws.send_json({"type": "user_message", "text": "/compact"})
            compacted = ws.receive_json()
            assert compacted["type"] == "compacted"
            assert compacted["before"] == 4
            assert compacted["after"] == 1

            ws.send_json({"type": "user_message", "text": "are you still there?"})
            messages = _receive_until(ws, "tasks_changed")

    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "still here"


def test_load_older_messages_reveals_pre_compact_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real, live-reported bug: after /compact, the chat log only ever
    showed the synthetic summary note -- no way to scroll up and see the
    real conversation, even though it was never actually deleted (see
    ChatSessionLG.load_older_messages' own docstring for the checkpoint
    mechanics). This is the fix's own regression test: the pre-compact
    turns come back verbatim on a "load_older_messages" request."""
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="hi there!"),
            AIMessage(content="nice to hear"),
            AIMessage(content="a short summary of the chat"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_older1") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "how are you"})
            _receive_until(ws, "tasks_changed")

            ws.send_json({"type": "user_message", "text": "/compact"})
            compacted = ws.receive_json()
            assert compacted["type"] == "compacted"

            ws.send_json({"type": "load_older_messages"})
            older = ws.receive_json()
            # has_more is a "try again" hint, not a real lookahead (see
            # load_older_messages' own docstring) -- true here even
            # though this genuinely is the last epoch, confirmed instead
            # by a *second* call actually coming back empty below.
            ws.send_json({"type": "load_older_messages"})
            second_call = ws.receive_json()

    assert older["type"] == "older_messages"
    assert older["has_more"] is True
    texts = [(e["kind"], e.get("text")) for e in older["entries"]]
    assert texts == [
        ("user", "hello"),
        ("agent", "hi there!"),
        ("user", "how are you"),
        ("agent", "nice to hear"),
    ]
    assert second_call == {"type": "older_messages", "entries": [], "has_more": False}


def test_load_older_messages_is_empty_when_the_thread_was_never_compacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_older2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")

            ws.send_json({"type": "load_older_messages"})
            older = ws.receive_json()

    assert older == {"type": "older_messages", "entries": [], "has_more": False}


def test_edit_message_truncates_history_and_regenerates_from_the_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="hi there!"),
            AIMessage(content="nice to hear"),
            AIMessage(content="edited reply"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_edit1") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "how are you"})
            _receive_until(ws, "tasks_changed")

            # index 1 -- the latest user turn -- edited. That turn onward
            # ("how are you", "nice to hear") is discarded, and the edited
            # text runs as a fresh turn; the earlier turn is untouched.
            ws.send_json({"type": "edit_message", "index": 1, "text": "how are you, edited"})
            messages = _receive_until(ws, "tasks_changed")

        # Reconnecting re-reads straight from the checkpointer -- proves
        # the truncation is real, not just a client-side illusion.
        with client.websocket_connect("/ws/t_edit1") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "edited reply"
    assert history["entries"] == [
        {"kind": "user", "text": "hello"},
        {"kind": "agent", "text": "hi there!"},
        {"kind": "user", "text": "how are you, edited"},
        {"kind": "agent", "text": "edited reply"},
    ]


def test_history_is_empty_for_a_brand_new_thread_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_hist_new") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert history == {"type": "history", "entries": [], "has_older": False}


def test_history_reports_has_older_true_after_reconnecting_to_a_compacted_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real, live-reported bug: the frontend's "load earlier messages"
    control used to be offered unconditionally on *every* thread,
    including a brand-new one with nothing to page through -- this
    `has_older` flag is what the frontend now gates that control on.
    Regression-tests the O(1) proxy itself: a thread that's been
    /compact'd, then reconnected to (a fresh connection, so send_history
    -- not any state left over from the compacting connection -- is what
    has to get this right), reports has_older=True."""
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="hi there!"),
            AIMessage(content="nice to hear"),
            AIMessage(content="a short summary of the chat"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_hist_has_older") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history -- empty, brand new thread
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "how are you"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "/compact"})
            assert ws.receive_json()["type"] == "compacted"

        with client.websocket_connect("/ws/t_hist_has_older") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert history["has_older"] is True


def test_reconnect_replays_conversation_history_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a real, live-reported bug: the chat log was
    only ever built from *live* events during the current WS connection,
    so switching to (or reconnecting to) an existing thread always showed
    a blank pane even though the model still remembered the whole
    conversation -- see serialize_history_for_ws_lg's docstring."""
    call = _tool_call("call_1", "read_file", {"path": "note.txt"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="the file says hello"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_hist_reconnect") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history -- empty, brand new thread
            ws.send_json({"type": "user_message", "text": "what does note.txt say?"})
            _receive_until(ws, "tasks_changed")

        # Reconnect -- a fresh WS connection to the same thread, exactly
        # what switching sessions or reloading the page does.
        with client.websocket_connect("/ws/t_hist_reconnect") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert history == {
        "type": "history",
        "entries": [
            {"kind": "user", "text": "what does note.txt say?"},
            {
                "kind": "tool",
                "tool_name": "read_file",
                "arguments": {"path": "note.txt"},
                "result": "File does not exist: note.txt",
                "is_error": True,
            },
            {"kind": "agent", "text": "the file says hello"},
        ],
        "has_older": False,
    }


def test_history_omits_a_call_still_pending_approval_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tool call awaiting approval has no ToolMessage result yet --
    serialize_history_for_ws_lg must skip it rather than show a
    phantom step with no outcome; resume_after_reconnect already
    redelivers the live approval_required event for it separately."""
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_hist_pending") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            # Disconnect without ever answering -- the call stays pending.

        with client.websocket_connect("/ws/t_hist_pending") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert history == {
        "type": "history",
        "entries": [{"kind": "user", "text": "write hi to note.txt"}],
        "has_older": False,
    }


def test_history_replay_includes_an_approved_calls_real_result_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a real, live-reported bug: reconnecting to (or
    reloading) an existing thread showed every past tool call as click-to-
    expand, but expanding one showed nothing -- ToolCallRow's own `result
    !== undefined` guard always failed on a replayed item, because
    serialize_history_for_ws_lg computed each call's real result (into
    results_by_id, to decide whether to include the entry at all) and then
    silently dropped it instead of putting it on the emitted entry. Uses
    an *approved* call specifically (not the plain read_file case the
    sibling reconnect test above already covers), since that's the
    real-world shape reported live -- an approval-gated run_command/
    write-file call whose result vanished on reload."""
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_hist_approved_result") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")

        with client.websocket_connect("/ws/t_hist_approved_result") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    tool_entry = next(e for e in history["entries"] if e["kind"] == "tool")
    assert tool_entry["result"] == {
        "path": "note.txt",
        "bytes_written": 2,
        "lines_added": 1,
        "lines_removed": 0,
    }
    assert tool_entry["is_error"] is False


def test_export_returns_the_conversation_as_a_markdown_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_export") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")
        response = client.get("/api/threads/t_export/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert 'filename="conversation-t_export.md"' in response.headers["content-disposition"]
    assert "## You\n\nhello" in response.text
    assert "## Coscribe\n\nhi there!" in response.text
