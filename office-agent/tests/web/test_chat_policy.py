# ruff: noqa: E402
"""Web tests: tool errors, the per-turn notes and the exec policy."""

import json
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from coscribe.runtime_lg.audit import AuditLog

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _stub_script_env,
    _tool_call,
)


def test_tool_raising_a_plain_exception_is_reported_to_the_model_not_a_crashed_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a real, live-reported bug: create_agent's
    ToolNode only converts a tool's raised exception into an error
    ToolMessage for its own ToolInvocationError -- a plain ValueError
    (exactly what every built-in coscribe tool raises for an ordinary
    "bad input" case, e.g. read_file's "File does not exist: ...") used to
    propagate all the way out of astream()/ainvoke(), hit
    _handle_user_message_locked's except Exception, and end the turn dead
    with a bare {"type": "error"} message -- no agent_message, no
    tasks_changed, indistinguishable from the turn hanging forever. Fixed
    by _CatchToolErrorsMiddleware (runtime_lg/agent.py) -- this proves the
    turn now completes normally instead, with the model seeing the error
    and getting to respond."""
    call = _tool_call("call_1", "read_file", {"path": "sap_login.md"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="sorry, that file doesn't exist"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_tool_error") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "read sap_login.md"})
            messages = _receive_until(ws, "tasks_changed")

    assert not any(m["type"] == "error" for m in messages)
    tool_result = next(m for m in messages if m["type"] == "tool_result")
    assert tool_result["tool_name"] == "read_file"
    assert "File does not exist" in str(tool_result["result"])
    # This same ToolMessage.status the middleware sets to "error" (see this
    # test's own docstring) is also what the transcript's failure styling
    # keys off -- see wire.ts's ToolResultEvent.is_error.
    assert tool_result["is_error"] is True
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "sorry, that file doesn't exist"


def test_date_note_is_per_turn_message_content_not_baked_into_the_system_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caching regression test: the date note used to be glued onto the
    very front of the system prompt (recomputed only when the agent got
    rebuilt), which poisoned the entire prefix for any provider's
    prefix-based caching -- Anthropic cache_control, and just as much
    Gemini/OpenAI-compatible providers' automatic caching, no
    cache_control needed on their end for the damage to apply. Fixed by
    moving it into per-turn message content instead (see
    current_date_note's docstring in runtime_lg/messages.py) -- this
    tests both halves: the system prompt sent to the model stays frozen
    (no date in it), and the actual HumanMessage the model sees each turn
    still carries the date, so real-world grounding isn't lost."""
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_date_note") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")

    assert len(fake_model.received) == 1
    sent_messages = fake_model.received[0]
    system_messages = [m for m in sent_messages if isinstance(m, SystemMessage)]
    assert system_messages, "expected a system message in the request"
    assert "Today's real date" not in system_messages[0].content

    human_messages = [m for m in sent_messages if isinstance(m, HumanMessage)]
    assert human_messages, "expected a human message in the request"
    today = datetime.now().strftime("%Y-%m-%d")
    assert human_messages[-1].content.startswith(f"Today's real date is {today} (")


def test_a_chinese_message_tells_the_model_to_narrate_in_chinese_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Asked in Chinese, deepseek-flash wrote every between-step note of a
    fresh conversation in English; the note is what the model sees, never
    what the history or the sidebar show."""
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="好的")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_zh") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "帮我做 Q3 经营回顾"})
            _receive_until(ws, "tasks_changed")
        with client.websocket_connect("/ws/t_zh") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()
        threads = client.get("/api/threads").json()

    human = [m for m in fake_model.received[0] if isinstance(m, HumanMessage)][-1]
    assert "[The user writes in Chinese:" in human.content
    assert human.content.endswith("帮我做 Q3 经营回顾")
    user_entries = [e for e in history["entries"] if e["kind"] == "user"]
    assert [e["text"] for e in user_entries] == ["帮我做 Q3 经营回顾"]
    assert threads[0]["preview"].startswith("帮我做")


def test_exec_policy_allow_rule_skips_approval_and_runs_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_script_env(monkeypatch)
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text(
        json.dumps({"rules": [{"pattern": r"print\(", "decision": "allow"}]}), encoding="utf-8"
    )
    call = _tool_call(
        "call_1", "run_python_script", {"script": "print('ok')", "description": "print ok"}
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, exec_policy_path=policy_path) as client:
        with client.websocket_connect("/ws/t_exec1") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "run it"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    assert "tool_result" in types

    entries = AuditLog(tmp_path / "state").read_all()
    assert len(entries) == 1
    assert entries[0].tool_name == "run_python_script"
    assert entries[0].decision == "approve"
    assert entries[0].reason == "exec_policy"


def test_exec_policy_forbidden_rule_rejects_without_approval_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_script_env(monkeypatch)
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "pattern": r"shutil\.rmtree",
                        "decision": "forbidden",
                        "justification": "no bulk deletes",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    call = _tool_call(
        "call_1",
        "run_python_script",
        {"script": "import shutil; shutil.rmtree('/tmp/x')", "description": "delete a dir"},
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, exec_policy_path=policy_path) as client:
        with client.websocket_connect("/ws/t_exec2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "run it"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    tool_result = next(m for m in messages if m["type"] == "tool_result")
    assert "no bulk deletes" in json.dumps(tool_result)

    entries = AuditLog(tmp_path / "state").read_all()
    assert len(entries) == 1
    assert entries[0].tool_name == "run_python_script"
    assert entries[0].decision == "reject"
    assert entries[0].reason == "exec_policy"
    assert entries[0].detail == "no bulk deletes"


def test_exec_policy_no_match_falls_through_to_normal_approval_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_script_env(monkeypatch)
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text(
        json.dumps({"rules": [{"pattern": r"this-does-not-appear", "decision": "allow"}]}),
        encoding="utf-8",
    )
    call = _tool_call(
        "call_1", "run_python_script", {"script": "print('ok')", "description": "print ok"}
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, exec_policy_path=policy_path) as client:
        with client.websocket_connect("/ws/t_exec3") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "run it"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_required"
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")

    entries = AuditLog(tmp_path / "state").read_all()
    assert entries[0].reason == "human"


def test_exec_policy_allow_does_not_override_plan_mode_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_script_env(monkeypatch)
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text(
        json.dumps({"rules": [{"pattern": r"print\(", "decision": "allow"}]}), encoding="utf-8"
    )
    call = _tool_call(
        "call_1", "run_python_script", {"script": "print('ok')", "description": "print ok"}
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="", tool_calls=[call]), AIMessage(content="done")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, exec_policy_path=policy_path) as client:
        with client.websocket_connect("/ws/t_exec4") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/plan"})
            ws.receive_json()  # state (plan_mode: True)

            ws.send_json({"type": "user_message", "text": "run it"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    entries = AuditLog(tmp_path / "state").read_all()
    assert entries[0].decision == "reject"
    assert entries[0].reason == "plan_mode"
