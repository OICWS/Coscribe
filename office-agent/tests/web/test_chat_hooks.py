# ruff: noqa: E402
"""Web tests: the hook commands run around tool calls and the turn."""

import json
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
)

from coscribe.runtime_lg.audit import AuditLog

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


def test_pretool_use_hook_denial_blocks_a_call_even_in_accept_edits_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook_script = tmp_path / "deny_hook.py"
    hook_script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        'sys.exit(1 if payload.get("tool_name") == "write_file" else 0)\n',
        encoding="utf-8",
    )
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(
        json.dumps({"PreToolUse": [f"{sys.executable} {hook_script}"]}), encoding="utf-8"
    )
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="denied by hook"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, hooks_config_path=hooks_path) as client:
        with client.websocket_connect("/ws/t4g") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/accept-edits"})
            ws.receive_json()  # state

            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "denied by hook"

    entries = AuditLog(tmp_path / "state").read_all()
    assert len(entries) == 1
    assert entries[0].decision == "reject"
    assert entries[0].reason == "hook_veto"
    assert entries[0].detail is not None
    assert not (tmp_path / "workspace" / "note.txt").exists()


def test_pretool_use_hook_gates_a_low_risk_tool_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When PreToolUse hooks are configured, even a tool that never
    required approval (task_create, risk_category="READ") is routed through the
    same interrupt point so the hook can veto it -- see agent.py's
    extra_interrupt_tool_names. It's still auto-approved (no
    approval_required sent) since the hook allows it and it was never
    risky enough to ask the user either way."""
    hook_script = tmp_path / "log_hook.py"
    log_path = tmp_path / "pretool.log"
    hook_script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        f'open({str(log_path)!r}, "a").write(payload["tool_name"] + chr(10))\n'
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(
        json.dumps({"PreToolUse": [f"{sys.executable} {hook_script}"]}), encoding="utf-8"
    )
    call = _tool_call("call_1", "task_create", {"content": "write the report"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="tracked it"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, hooks_config_path=hooks_path) as client:
        with client.websocket_connect("/ws/t4h") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "please plan this out"})
            messages = _receive_until(ws, "tasks_changed")

    types = [m["type"] for m in messages]
    assert "approval_required" not in types
    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "tracked it"
    assert log_path.read_text(encoding="utf-8").strip() == "task_create"


def test_post_tool_use_hook_receives_the_tool_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook_script = tmp_path / "posttool_hook.py"
    log_path = tmp_path / "posttool.log"
    hook_script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        f'open({str(log_path)!r}, "a").write(json.dumps(payload) + chr(10))\n'
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(
        json.dumps({"PostToolUse": [f"{sys.executable} {hook_script}"]}), encoding="utf-8"
    )
    call = _tool_call("call_1", "write_file", {"path": "note.txt", "content": "hi"})
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[call]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, hooks_config_path=hooks_path) as client:
        with client.websocket_connect("/ws/t4i") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write hi to note.txt"})
            approval = ws.receive_json()
            ws.send_json({"type": "approval_response", "id": approval["id"], "approved": True})
            _receive_until(ws, "tasks_changed")

    logged = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert logged["tool_name"] == "write_file"
    assert logged["arguments"] == {"path": "note.txt", "content": "hi"}
    assert logged["result"]["bytes_written"] == 2


def _wait_for_file(path: Path, timeout: float = 10.0) -> None:
    """Some hook events (Interrupt, SessionEnd) fire from a background
    task/exception handler rather than inline with a message the test can
    wait on with ws.receive_json() -- unlike a normal request/response
    exchange, there's no built-in synchronization point proving the
    server has actually finished running the hook by the time the test's
    own code continues, so this polls briefly instead of asserting
    immediately."""
    deadline = time.monotonic() + timeout
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)


def _logging_hook_config(tmp_path: Path, event: str, log_path: Path) -> Path:
    """Same pattern as test_post_tool_use_hook_receives_the_tool_result
    above: a hook script that appends its received JSON payload to
    log_path, one line per invocation -- shared by the Phase 7 item 3
    event tests below (SessionEnd/UserPromptSubmit/PreCompact/
    PostCompact/Interrupt) since they all just need to prove the payload
    actually arrived, not exercise anything event-specific about how the
    hook script itself behaves."""
    hook_script = tmp_path / f"{event.lower()}_hook.py"
    hook_script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        f'open({str(log_path)!r}, "a").write(json.dumps(payload) + chr(10))\n'
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(
        json.dumps({event: [f"{sys.executable} {hook_script}"]}), encoding="utf-8"
    )
    return hooks_path


def test_user_prompt_submit_hook_receives_the_message_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = tmp_path / "log.jsonl"
    hooks_path = _logging_hook_config(tmp_path, "UserPromptSubmit", log_path)
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model, hooks_config_path=hooks_path) as client:
        with client.websocket_connect("/ws/t_hook_ups") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello there"})
            _receive_until(ws, "tasks_changed")

    logged = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert logged["event"] == "UserPromptSubmit"
    assert logged["text"] == "hello there"


def test_pre_and_post_compact_hooks_fire_around_manual_compact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pre_log = tmp_path / "pre.jsonl"
    post_log = tmp_path / "post.jsonl"
    pre_script = tmp_path / "pre_hook.py"
    pre_script.write_text(
        "import json, sys\n"
        "json.load(sys.stdin)\n"
        f'open({str(pre_log)!r}, "a").write("fired\\n")\n'
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    post_script = tmp_path / "post_hook.py"
    post_script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        f'open({str(post_log)!r}, "a").write(json.dumps(payload) + chr(10))\n'
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    hooks_path = tmp_path / "hooks.json"
    hooks_path.write_text(
        json.dumps(
            {
                "PreCompact": [f"{sys.executable} {pre_script}"],
                "PostCompact": [f"{sys.executable} {post_script}"],
            }
        ),
        encoding="utf-8",
    )
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content=f"reply {i}") for i in range(6)]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model, hooks_config_path=hooks_path) as client:
        with client.websocket_connect("/ws/t_hook_compact") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            for i in range(3):
                ws.send_json({"type": "user_message", "text": f"message {i}"})
                _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "/compact"})
            compacted = ws.receive_json()
            assert compacted["type"] == "compacted"

    assert pre_log.read_text(encoding="utf-8").strip() == "fired"
    logged = json.loads(post_log.read_text(encoding="utf-8").strip())
    assert logged["event"] == "PostCompact"
    assert logged["before"] == compacted["before"]
    assert logged["after"] == compacted["after"]


def test_interrupt_hook_fires_on_a_stop_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = tmp_path / "log.jsonl"
    hooks_path = _logging_hook_config(tmp_path, "Interrupt", log_path)
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model, hooks_config_path=hooks_path) as client:
        with client.websocket_connect("/ws/t_hook_interrupt") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "stop"})
            _wait_for_file(log_path)

    logged = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert logged["event"] == "Interrupt"
    assert logged["thread_id"] == "t_hook_interrupt"


def test_session_end_hook_fires_on_disconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_path = tmp_path / "log.jsonl"
    hooks_path = _logging_hook_config(tmp_path, "SessionEnd", log_path)
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model, hooks_config_path=hooks_path) as client:
        with client.websocket_connect("/ws/t_hook_end") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            # Close explicitly and wait *inside* this `with` block, same
            # pattern as test_interrupt_hook_fires_on_a_stop_message right
            # above -- not incidental. Found live, genuinely flaky (not a
            # CI-only artifact -- reproduced locally too): starlette's own
            # WebSocketTestSession.__exit__ (relied on if this block is
            # left to close the socket implicitly on exit) sends the
            # disconnect message and then *immediately* hard-cancels the
            # whole in-flight ASGI app task via its cancel scope, racing
            # ahead of app.py's own `except WebSocketDisconnect:` handler
            # actually finishing `await session.run_session_end_hooks()`
            # (which shells out to a real subprocess) -- confirmed by
            # reading starlette/testclient.py's own __exit__/_run methods,
            # not guessed. Closing here instead means the wait below has
            # real, uncancelled wall-clock time for the hook to actually
            # run before this `with` block's own __exit__ can race it.
            ws.close()
            _wait_for_file(log_path)

    logged = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert logged["event"] == "SessionEnd"
    assert logged["thread_id"] == "t_hook_end"
