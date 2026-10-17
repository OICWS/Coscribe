# ruff: noqa: E402
"""Web tests: the model asking the user a question, and redelivery after a reconnect."""

import json
import sys
from pathlib import Path

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


def test_ask_user_question_sends_question_required_and_feeds_answer_back_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call(
        "call_1",
        "ask_user_question",
        {
            "questions": [
                {
                    "question": "What kind of plan?",
                    "header": "Plan type",
                    "options": [
                        {"label": "Travel", "description": "Flights, hotels, a route"},
                        {"label": "Study"},
                    ],
                },
                {
                    "question": "Which days?",
                    "options": [{"label": "Weekdays"}, {"label": "Weekends"}],
                    "multi_select": True,
                },
                {"question": "Budget?", "options": [{"label": "Low"}, {"label": "High"}]},
            ]
        },
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q1") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "help me plan something"})

            question = ws.receive_json()
            assert question["type"] == "question_required"
            assert [q["question"] for q in question["questions"]] == [
                "What kind of plan?",
                "Which days?",
                "Budget?",
            ]
            assert question["questions"][0]["header"] == "Plan type"
            assert question["questions"][0]["options"] == [
                {"label": "Travel", "description": "Flights, hotels, a route"},
                {"label": "Study", "description": ""},
            ]
            assert [q["multi_select"] for q in question["questions"]] == [False, True, False]

            ws.send_json(
                {
                    "type": "question_response",
                    "id": question["id"],
                    "answers": ["Travel", "Weekdays, Weekends", None],
                }
            )
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    # No "tool_result" WS event either: the question_required/answered card
    # already fully represents this call, so session.py deliberately skips
    # sending the normal tool_result event for QUESTION_TOOL_NAMES (it would
    # otherwise show up as a redundant second "Asked: ..." row in the log --
    # see _stream_turn's ToolMessage branch). Confirm the answer really did
    # feed back into the model instead by inspecting the follow-up call.
    assert "tool_result" not in types
    tool_messages = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    assert tool_messages[-1].name == "ask_user_question"
    assert tool_messages[-1].content == (
        "1. What kind of plan? -> Travel\n"
        "2. Which days? -> Weekdays, Weekends\n"
        "3. Budget? -> (skipped)"
    )
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "done"


def test_closing_the_questions_tells_the_model_to_go_on_without_asking_again_lg(
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
        with client.websocket_connect("/ws/t_q1b") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "ask me something"})
            question = ws.receive_json()
            ws.send_json({"type": "question_response", "id": question["id"], "dismissed": True})
            _receive_until(ws, "tasks_changed")

    tool_messages = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    assert "closed the questions without answering" in str(tool_messages[-1].content)


def test_ask_user_question_free_text_answer_works_too_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The user can always type a custom answer instead of clicking a
    listed option -- there's nothing server-side that validates the
    answer against `options` at all, matching AskUserQuestion's own
    "Other" escape hatch."""
    call = _tool_call(
        "call_1",
        "ask_user_question",
        {"question": "What kind of plan?", "options": "Travel\nStudy"},
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "help me plan something"})

            question = ws.receive_json()
            ws.send_json(
                {
                    "type": "question_response",
                    "id": question["id"],
                    "answer": "Actually, a birthday party",
                }
            )
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "tool_result" not in types
    tool_messages = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    assert "birthday party" in json.dumps(tool_messages[-1].content)


def test_ask_user_question_is_not_blocked_by_plan_mode_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unlike a WRITE_LOCAL/EXEC/EXTERNAL tool, asking a question isn't a
    risky action plan mode's read-only guarantee needs to block -- it's
    pure communication, no side effect."""
    call = _tool_call("call_1", "ask_user_question", {"question": "Which one?", "options": "A\nB"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q3") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/plan"})
            ws.receive_json()  # state (plan_mode: True)

            ws.send_json({"type": "user_message", "text": "ask me something"})
            question = ws.receive_json()
            assert question["type"] == "question_required"
            ws.send_json({"type": "question_response", "id": question["id"], "answer": "A"})
            _receive_until(ws, "tasks_changed")


def test_ask_user_question_hook_veto_becomes_a_respond_decision_not_a_reject_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A PreToolUse hook can still veto ask_user_question, but the
    HumanInTheLoopMiddleware interrupt for this tool only allows a
    "respond" decision -- a bare {"type": "reject", ...} would raise
    inside the middleware, so the veto reason has to be delivered as the
    tool's own "answer" instead."""
    hook_script = tmp_path / "veto_hook.py"
    hook_script.write_text("import sys; sys.stderr.write('no questions allowed'); sys.exit(1)\n")
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(
        json.dumps({"PreToolUse": [f"{sys.executable} {hook_script}"]}), encoding="utf-8"
    )
    call = _tool_call("call_1", "ask_user_question", {"question": "Which one?", "options": "A\nB"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="blocked")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, hooks_config_path=hooks_path) as client:
        with client.websocket_connect("/ws/t_q4") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "ask me something"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "question_required" not in types
    assert "tool_result" not in types
    tool_messages = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    assert "no questions allowed" in json.dumps(tool_messages[-1].content)
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "blocked"


def test_stop_resolves_a_pending_question_with_a_placeholder_answer_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves request_stop() resolves a pending question rather than
    leaving the turn hanging forever -- the same "[stopped]" fallback text
    test_stop_denies_pending_approval_and_marks_reply_stopped's approval
    case gets (see _stream_turn's reply_text fallback), since the resumed
    astream's own cooperative stop check (checked after every chunk,
    including the ToolNode's ToolMessage carrying the placeholder answer)
    breaks the loop before any further model narration exists to report.
    The placeholder's actual content ("(Stopped by user before
    answering.)") isn't independently observable over the wire once
    resolved this way -- ask_user_question's tool_result WS event is
    deliberately suppressed (see _stream_turn's ToolMessage branch), same
    as the non-stopped answer path above -- so this only checks the
    contract a client actually sees: the turn ends promptly, not that it
    hangs waiting on a future nobody will ever resolve."""
    call = _tool_call("call_1", "ask_user_question", {"question": "Which one?", "options": "A\nB"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="stopped")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q5") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "ask me something"})
            question = ws.receive_json()
            assert question["type"] == "question_required"

            ws.send_json({"type": "stop"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "tool_result" not in types
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "[stopped]"


def test_ask_user_question_still_reads_a_single_question_with_line_options_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call(
        "call_1",
        "ask_user_question",
        {
            "question": "Which ones?",
            "options": "A\n\nB\nC\n",
            "multi_select": True,
        },
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_q6") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "ask me something"})
            question = ws.receive_json()
            # A call saved in a conversation from before questions came in
            # lists still shows: one question, its options one per line,
            # blank lines dropped.
            (only,) = question["questions"]
            assert only["multi_select"] is True
            assert [option["label"] for option in only["options"]] == ["A", "B", "C"]

            ws.send_json({"type": "question_response", "id": question["id"], "answer": "A, C"})
            _receive_until(ws, "tasks_changed")


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
    call = _tool_call(
        "call_1",
        "ask_user_question",
        {"questions": [{"question": "Budget?", "options": [{"label": "Low"}, {"label": "High"}]}]},
    )
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
            ws.send_json({"type": "question_response", "id": question["id"], "answers": ["Low"]})
            messages = _receive_until(ws, "tasks_changed")

    assert next(m for m in messages if m["type"] == "agent_message")["text"] == "done"
