# ruff: noqa: E402
"""Web tests: denying and stopping a turn, clearing, and healing orphaned tool calls."""

import asyncio
import contextlib
import threading
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from coscribe.runtime_lg.audit import AuditLog

from .helpers import (
    FakeToolCallingChatModel,
    HangingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


def test_write_file_denied_is_not_executed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="ok, cancelled"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t3") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})

            approval = ws.receive_json()
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": False})
            messages = _receive_until(ws, "tasks_changed")

    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "ok, cancelled"
    assert not (tmp_path / "workspace" / "note.txt").exists()

    entries = AuditLog(tmp_path / "state").read_all()
    assert len(entries) == 1
    assert entries[0].decision == "reject"
    assert entries[0].reason == "human"


def test_clear_queues_behind_a_pending_turn_instead_of_racing_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression coverage for _turn_lock (see its docstring in __init__):
    a message sent while a turn is still pending on approval must *queue*
    behind it, not run concurrently -- so /clear here can't even reach its
    own "is anything pending?" check until the first turn's approval is
    answered and that turn fully finishes. Before _turn_lock existed, this
    exact scenario used to run /clear concurrently and see the pending
    approval immediately (asserted as an error); now it can't be observed
    at all through this path, since the lock always resolves the earlier
    turn first -- see _handle_clear's docstring for the one narrow window
    where that guard is still reachable."""
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_clear2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"

            # Queues behind _turn_lock -- nothing happens with this until
            # the pending approval below is answered.
            ws.send_json({"type": "user_message", "text": "/clear"})

            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            first_turn_messages = _receive_until(ws, "tasks_changed")
            cleared = ws.receive_json()

    assert cleared == {"type": "cleared"}
    agent_message = next(m for m in first_turn_messages if m["type"] == "agent_message")
    assert agent_message["text"] == "done"


def test_stop_denies_pending_approval_and_marks_reply_stopped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_stop") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"

            ws.send_json({"type": "stop"})
            messages = _receive_until(ws, "tasks_changed")

    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert "[stopped]" in agent_message["text"]
    assert not (tmp_path / "workspace" / "note.txt").exists()


def test_stop_hard_cancels_a_turn_stuck_inside_the_model_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real, user-reported bug: a provider SDK stuck in its own internal
    retry/backoff loop (e.g. langchain_google_genai on a Gemini quota
    error) never yields a chunk for the cooperative _stop_requested check
    to run against, so Stop did nothing for however long that loop ran
    (up to ~60-90s). request_stop() now hard-cancels the turn's own task
    whenever there's nothing pending to resolve instead (see its
    docstring) -- this proves the cancellation actually reaches a call
    genuinely stuck mid-stream, not just one paused between chunks."""
    started = threading.Event()
    fake_model = HangingChatModel(started=started)
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_hard_stop") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})

            # Wait until the turn has genuinely entered the hanging model
            # call (and _current_turn_task is therefore assigned) before
            # sending stop -- otherwise this races request_stop() against
            # handle_user_message's own task assignment.
            assert started.wait(timeout=5), "model call never started"

            ws.send_json({"type": "stop"})
            # HangingChatModel's _astream awaits asyncio.sleep(999) -- if
            # cancellation isn't actually reaching it, this receive blocks
            # for the test's own default timeout and fails loudly rather
            # than hanging for 999s.
            agent_message = ws.receive_json()
            # The task panel refreshes on this after any turn, a stopped one too.
            refresh = ws.receive_json()

    assert agent_message["type"] == "agent_message"
    assert agent_message["text"] == "[stopped]"
    assert refresh["type"] == "tasks_changed"


def test_close_orphaned_tool_calls_commits_a_finished_parallel_calls_uncommitted_result() -> None:
    """Parallel tool calls, cancelled while one is still running: the one
    that finished only has an uncommitted pending write, which aget_state
    shows but a fresh input would drop. Its real result must survive, and
    only the unfinished call gets the placeholder."""
    from langchain.agents import create_agent
    from langchain_core.messages import ToolCall
    from langgraph.checkpoint.memory import InMemorySaver

    from coscribe.conversation.history import (
        close_orphaned_tool_calls as _close_orphaned_tool_calls,
    )
    from coscribe.conversation.session import _ORPHANED_TOOL_CALL_NOTE

    started = threading.Event()
    release = threading.Event()

    def fast(q: str) -> str:
        """Fast lookup."""
        return "fast result"

    def slow(q: str) -> str:
        """Slow lookup."""
        started.set()
        release.wait(timeout=10)
        return "slow result"

    model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    ToolCall(name="fast", args={"q": "a"}, id="fast_call"),
                    ToolCall(name="slow", args={"q": "b"}, id="slow_call"),
                ],
            ),
            AIMessage(content="hi"),
        ]
    )
    agent = create_agent(model, [fast, slow], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t"}}

    async def scenario() -> None:
        turn = asyncio.create_task(
            agent.ainvoke({"messages": [HumanMessage(content="go")]}, config)
        )
        await asyncio.to_thread(started.wait, 5)
        await asyncio.sleep(0.2)
        turn.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await turn
        release.set()
        assert await _close_orphaned_tool_calls(agent, config) is True
        await agent.ainvoke({"messages": [HumanMessage(content="say hi")]}, config)

    try:
        asyncio.run(scenario())
    finally:
        release.set()

    history = model.received[-1]
    tool_messages = {m.tool_call_id: m.content for m in history if isinstance(m, ToolMessage)}
    assert tool_messages == {"fast_call": "fast result", "slow_call": _ORPHANED_TOOL_CALL_NOTE}
    assert isinstance(history[-1], HumanMessage)


def test_close_orphaned_tool_calls_commits_a_finished_tools_uncommitted_write() -> None:
    """Every tool call finished, but the superstep never committed: the
    ToolMessage exists only as a pending write, visible through aget_state
    yet dropped by a fresh input -- the exact state a live DeepSeek thread
    was found in. Nothing needs a placeholder; the write must still be
    committed or the model sees the orphan anyway."""
    from langchain.agents import create_agent
    from langchain_core.messages import ToolCall
    from langgraph.checkpoint.memory import InMemorySaver

    from coscribe.conversation.history import (
        close_orphaned_tool_calls as _close_orphaned_tool_calls,
    )

    def lookup(q: str) -> str:
        """Look something up."""
        return "unused"

    checkpointer = InMemorySaver()
    model = FakeToolCallingChatModel(responses=[AIMessage(content="hi")])
    agent = create_agent(model, [lookup], checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "t"}}
    call = ToolCall(name="lookup", args={"q": "a"}, id="call_1")

    async def scenario() -> None:
        await agent.aupdate_state(
            config,
            {"messages": [HumanMessage(content="go"), AIMessage(content="", tool_calls=[call])]},
            as_node="model",
        )
        state = await agent.aget_state(config)
        await checkpointer.aput_writes(
            state.config,
            [("messages", [ToolMessage(content="real result", tool_call_id="call_1")])],
            state.tasks[0].id,
        )
        assert await _close_orphaned_tool_calls(agent, config) is True
        await agent.ainvoke({"messages": [HumanMessage(content="say hi")]}, config)

    asyncio.run(scenario())

    history = model.received[-1]
    assert [type(m).__name__ for m in history] == [
        "HumanMessage",
        "AIMessage",
        "ToolMessage",
        "HumanMessage",
    ]
    assert history[2].content == "real result"
