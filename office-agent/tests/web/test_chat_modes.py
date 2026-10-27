# ruff: noqa: E402
"""Web tests: switching model, plan mode, accept-edits, auto mode and the default mode."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
)

from coscribe.conversation import session as conversation_session
from coscribe.runtime_lg.audit import AuditLog
from coscribe.runtime_lg.effort import runs_as

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _start_mode,
    _tool_call,
    _verdict,
    _write_call,
)


def test_switch_model_rebuilds_the_graph_and_reports_the_new_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model_a = FakeToolCallingChatModel(responses=[AIMessage(content="hi from A")])
    fake_model_b = FakeToolCallingChatModel(responses=[AIMessage(content="hi from B")])
    models = {"fake:model": fake_model_a, "fake:model-b": fake_model_b}
    with _client_lg(tmp_path, monkeypatch, fake_model_a) as client:
        # Must be set *after* entering _client_lg -- its own body sets a
        # default stub for resolve_chat_model on entry, which would
        # otherwise overwrite this one (same gotcha as
        # connect_one_mcp_server_lg elsewhere in this file).
        monkeypatch.setattr(
            conversation_session,
            "resolve_chat_model",
            lambda model, custom_providers=None: models[model],
        )
        with client.websocket_connect("/ws/t_switch") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history
            assert state["model"] == "fake:model"

            ws.send_json({"type": "switch_model", "model": "fake:model-b"})
            switched_state = ws.receive_json()
            assert switched_state["type"] == "state"
            assert switched_state["model"] == "fake:model-b"

            ws.send_json({"type": "user_message", "text": "hello"})
            messages = _receive_until(ws, "tasks_changed")

    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "hi from B"


def test_switch_model_with_an_effort_rebuilds_the_model_at_that_level_and_refuses_an_unknown_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi")])
    levels_asked: list[str] = []

    def for_conversation(model: object, thread_id: str, effort: str) -> tuple[object, str | None]:
        levels_asked.append(effort)
        return model, runs_as(effort, ("low", "high"))

    monkeypatch.setattr(conversation_session, "for_conversation", for_conversation)
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_effort") as ws:
            state = ws.receive_json()
            ws.receive_json()  # history
            assert (state["effort"], state["effort_runs_as"]) == ("medium", "low")

            ws.send_json({"type": "switch_model", "model": "fake:model", "effort": "ultra"})
            changed = ws.receive_json()
            assert (changed["effort"], changed["effort_runs_as"]) == ("ultra", "high")

            ws.send_json({"type": "switch_model", "model": "fake:model", "effort": "huge"})
            assert ws.receive_json()["type"] == "error"

            ws.send_json({"type": "user_message", "text": "hello"})
            messages = _receive_until(ws, "tasks_changed")

    assert levels_asked[-1] == "huge"
    assert next(m for m in messages if m["type"] == "agent_message")["text"] == "hi"


def test_plan_mode_toggle_updates_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="unused")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t4") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/plan"})
            state = ws.receive_json()
            assert state == {
                "type": "state",
                "plan_mode": True,
                "accept_edits": False,
                "model": "fake:model",
                "effort": "medium",
                "effort_runs_as": None,
                "context_window": 128_000,
                "enabled_skills": [
                    "Docs",
                    "Excel Spreadsheets",
                    "PPTX Pages",
                    "PPTX Slides",
                    "SVG and HTML Design",
                    "Skill Creator",
                    "Word Documents",
                ],
                "workspace_root": str(tmp_path / "workspace"),
                "workspace_explicit": False,
                "folders": [],
                "environment": "default",
                "connector_tools": [],
                "auto_mode": False,
            }
            ws.send_json({"type": "user_message", "text": "/plan"})
            state = ws.receive_json()
            assert state["plan_mode"] is False


def test_accept_edits_toggle_updates_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="unused")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t4b") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/accept-edits"})
            state = ws.receive_json()
            assert state["accept_edits"] is True


def test_plan_mode_blocks_write_file_without_asking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="blocked"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t4c") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/plan"})
            ws.receive_json()  # state (plan_mode: True)

            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "blocked"

    entries = AuditLog(tmp_path / "state").read_all()
    assert len(entries) == 1
    assert entries[0].decision == "reject"
    assert entries[0].reason == "plan_mode"
    assert not (tmp_path / "workspace" / "note.txt").exists()


def test_accept_edits_auto_approves_without_asking(
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
        with client.websocket_connect("/ws/t4d") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/accept-edits"})
            ws.receive_json()  # state (accept_edits: True)

            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "done"
    assert (tmp_path / "workspace" / "note.txt").read_text() == "hi"

    entries = AuditLog(tmp_path / "state").read_all()
    assert len(entries) == 1
    assert entries[0].decision == "approve"
    assert entries[0].reason == "accept_edits"


def test_accept_edits_still_asks_before_running_code_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = _tool_call("c1", "run_python_script", {"script": "print(1)", "description": "print"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[run]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_accept_exec") as ws:
            _start_mode(ws, "/accept-edits")
            ws.send_json({"type": "user_message", "text": "run it"})
            approval = _receive_until(ws, "approval_required")[-1]
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": False})
            _receive_until(ws, "tasks_changed")

    assert approval["tool_name"] == "run_python_script"


def test_auto_mode_runs_what_the_reviewer_allows_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_write_call("c1", "note.txt")]),
            _verdict("allow", "writing the note the user asked for"),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_auto_allow") as ws:
            state = _start_mode(ws, "/auto")
            ws.send_json({"type": "user_message", "text": "write the note"})
            messages = _receive_until(ws, "tasks_changed")

    assert state["auto_mode"] is True
    assert not any(m["type"] == "approval_required" for m in messages)
    assert (tmp_path / "workspace" / "note.txt").read_text() == "hi"
    review_request = str(fake_model.received[1][-1].content)
    assert "write_file(" in review_request
    assert "write the note" in review_request


def test_auto_mode_refuses_what_the_reviewer_blocks_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_write_call("c1", "old.txt")]),
            _verdict("block", "old.txt existed before this conversation."),
            AIMessage(content="I'll ask first."),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_auto_block") as ws:
            _start_mode(ws, "/auto")
            ws.send_json({"type": "user_message", "text": "overwrite old.txt"})
            messages = _receive_until(ws, "tasks_changed")

    assert not any(m["type"] == "approval_required" for m in messages)
    assert not (tmp_path / "workspace" / "old.txt").exists()
    refusal = str(fake_model.received[2][-1].content)
    assert "Auto mode blocked this: old.txt existed before this conversation." in refusal


def test_auto_mode_asks_after_three_blocks_in_a_row_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_write_call("c1", "a.txt")]),
            _verdict("block", "no"),
            AIMessage(content="", tool_calls=[_write_call("c2", "b.txt")]),
            _verdict("block", "no"),
            AIMessage(content="", tool_calls=[_write_call("c3", "c.txt")]),
            _verdict("block", "still no"),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_auto_fallback") as ws:
            _start_mode(ws, "/auto")
            ws.send_json({"type": "user_message", "text": "write the files"})
            approval = _receive_until(ws, "approval_required")[-1]
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")

    assert approval["arguments"]["path"] == "c.txt"
    assert "still no" in approval["reviewer_note"]
    assert (tmp_path / "workspace" / "c.txt").exists()
    assert not (tmp_path / "workspace" / "a.txt").exists()


def test_approving_a_plan_leaves_plan_mode_for_auto_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exit_plan = _tool_call("c1", "exit_plan_mode", {"plan": "1. Write note.txt"})
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[exit_plan]), AIMessage(content="On it.")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_plan_exit") as ws:
            _start_mode(ws, "/plan")
            ws.send_json({"type": "user_message", "text": "plan the note"})
            plan = _receive_until(ws, "plan_ready")[-1]
            ws.send_json({"type": "question_response", "id": plan["id"], "answer": "auto"})
            messages = _receive_until(ws, "tasks_changed")

    assert plan["plan"] == "1. Write note.txt"
    state = next(m for m in messages if m["type"] == "state")
    assert (state["plan_mode"], state["auto_mode"]) == (False, True)
    result = str(fake_model.received[1][-1].content)
    assert "approved the plan and switched to auto mode" in result


def test_a_new_conversation_starts_in_the_default_mode_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model, default_permission_mode="auto") as client:
        with client.websocket_connect("/ws/t_default_auto") as ws:
            chat = ws.receive_json()
        with client.websocket_connect("/ws/scheduled-trig_x-run1") as ws:
            run = ws.receive_json()

    assert (chat["plan_mode"], chat["accept_edits"], chat["auto_mode"]) == (False, False, True)
    assert (run["plan_mode"], run["accept_edits"], run["auto_mode"]) == (False, False, False)


def test_the_default_mode_is_set_live_and_checked_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        bad = client.post(
            "/api/config", json={"updates": {"COSCRIBE_DEFAULT_PERMISSION_MODE": "yolo"}}
        )
        good = client.post(
            "/api/config", json={"updates": {"COSCRIBE_DEFAULT_PERMISSION_MODE": "plan"}}
        )
        with client.websocket_connect("/ws/t_default_plan") as ws:
            state = ws.receive_json()

    assert "COSCRIBE_DEFAULT_PERMISSION_MODE" in bad.json()["rejected"]
    assert good.json()["restart_required"] is False
    assert state["plan_mode"] is True


def test_modes_are_one_at_a_time_lg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_modes") as ws:
            plan = _start_mode(ws, "/plan")
            ws.send_json({"type": "user_message", "text": "/auto"})
            auto = ws.receive_json()
            ws.send_json({"type": "user_message", "text": "/auto"})
            manual = ws.receive_json()

    assert (plan["plan_mode"], plan["auto_mode"]) == (True, False)
    assert (auto["plan_mode"], auto["accept_edits"], auto["auto_mode"]) == (False, False, True)
    assert (manual["plan_mode"], manual["accept_edits"], manual["auto_mode"]) == (
        False,
        False,
        False,
    )
