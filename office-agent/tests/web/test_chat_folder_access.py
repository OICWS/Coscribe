# ruff: noqa: E402
"""Web tests: the model asking for a folder outside the workspace (decision 0048)."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage, ToolMessage

from coscribe.runtime import Environments
from coscribe.runtime_lg import AuditLog

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


def _outside(tmp_path: Path) -> Path:
    folder = tmp_path / "Contracts" / "2025"
    folder.mkdir(parents=True)
    (folder / "quote.txt").write_text("Quote 42", encoding="utf-8")
    return folder


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    folder: Path,
    answer: str,
    thread: str,
) -> tuple[list[ToolMessage], dict[str, object]]:
    monkeypatch.chdir(tmp_path)
    path = str(folder / "quote.txt")
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="", tool_calls=[_tool_call("c1", "read_file", {"path": path})]),
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call(
                        "c2",
                        "request_folder_access",
                        {"folder": str(folder), "access": "read", "reason": "to read the quotes"},
                    )
                ],
            ),
            AIMessage(content="", tool_calls=[_tool_call("c3", "read_file", {"path": path})]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect(f"/ws/{thread}") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "sum up the 2025 quotes"})
            card = _receive_until(ws, "folder_access_required")[-1]
            ws.send_json({"type": "question_response", "id": card["id"], "answer": answer})
            _receive_until(ws, "agent_message")
    tool_messages = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    return tool_messages, card


def test_a_refused_folder_tells_the_model_how_to_ask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _outside(tmp_path)
    messages, card = _run(tmp_path, monkeypatch, folder, "deny", "t_folder_deny")
    assert "request_folder_access" in str(messages[0].content)
    assert card["folder"] == str(folder.resolve())
    assert card["access"] == "read"
    assert card["reason"] == "to read the quotes"
    assert "didn't allow" in str(messages[1].content)
    assert "Quote 42" not in str(messages[2].content)


def test_allow_adds_the_folder_to_the_workspace_and_the_next_call_reaches_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _outside(tmp_path)
    messages, _ = _run(tmp_path, monkeypatch, folder, "allow:read", "t_folder_allow")
    assert "this workspace" in str(messages[1].content)
    assert "Quote 42" in str(messages[2].content)
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert f"COSCRIBE_EXTRA_READABLE_DIRS={folder.resolve()}" in env
    environments = Environments(tmp_path / "state")
    assert environments.thread_folders("t_folder_allow") == {}
    # Into Allowed folders, and used by this conversation's workspace only (decision 0053).
    assert str(folder.resolve()) in environments.for_thread("t_folder_allow")["folders"]
    [entry] = [
        e for e in AuditLog(tmp_path / "state").read_all() if e.tool_name == "request_folder_access"
    ]
    assert (entry.decision, entry.reason, entry.detail) == ("approve", "human", "allow:read")


def test_only_this_chat_keeps_the_folder_to_the_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _outside(tmp_path)
    messages, _ = _run(tmp_path, monkeypatch, folder, "chat:read-write", "t_folder_chat")
    assert "this conversation only" in str(messages[1].content)
    assert "Quote 42" in str(messages[2].content)
    assert not (tmp_path / ".env").exists() or "EXTRA" not in (tmp_path / ".env").read_text()
    granted = Environments(tmp_path / "state").thread_folders("t_folder_chat")
    assert granted == {str(folder.resolve()): "read-write"}


def test_a_folder_allowed_in_settings_reaches_an_open_conversation_without_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    folder = _outside(tmp_path)
    # The workspace already uses it; Allowed folders don't hold it yet.
    Environments(tmp_path / "state").use_folder(
        "t_folder_settings", str(folder), str(tmp_path / "workspace"), "Work"
    )
    path = str(folder / "quote.txt")
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="hello"),
            AIMessage(content="", tool_calls=[_tool_call("c1", "read_file", {"path": path})]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_folder_settings") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hi"})
            _receive_until(ws, "agent_message")
            saved = client.post(
                "/api/config", json={"updates": {"COSCRIBE_EXTRA_READABLE_DIRS": str(folder)}}
            )
            ws.send_json({"type": "user_message", "text": "read the quote"})
            _receive_until(ws, "agent_message")
    assert saved.json()["restart_required"] is False
    [read] = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    assert "Quote 42" in str(read.content)


def test_a_folder_taken_off_allowed_folders_leaves_an_open_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    folder = _outside(tmp_path)
    Environments(tmp_path / "state").use_folder(
        "t_folder_gone", str(folder), str(tmp_path / "workspace"), "Work"
    )
    path = str(folder / "quote.txt")
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="hello"),
            AIMessage(content="", tool_calls=[_tool_call("c1", "read_file", {"path": path})]),
            AIMessage(content="done"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        client.post("/api/config", json={"updates": {"COSCRIBE_EXTRA_READABLE_DIRS": str(folder)}})
        with client.websocket_connect("/ws/t_folder_gone") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hi"})
            _receive_until(ws, "agent_message")
            client.post("/api/config", json={"updates": {"COSCRIBE_EXTRA_READABLE_DIRS": ""}})
            ws.send_json({"type": "user_message", "text": "read the quote"})
            _receive_until(ws, "agent_message")
    stored = Environments(tmp_path / "state").for_thread("t_folder_gone")["folders"]
    assert str(folder) not in stored
    [read] = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    assert "Quote 42" not in str(read.content)

