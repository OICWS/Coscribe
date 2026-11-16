# ruff: noqa: E402
"""Web tests: the model asking for a folder outside the workspace (decision 0048)."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage, ToolMessage

from coscribe.runtime import Environments

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


def test_allow_adds_the_folder_everywhere_and_the_next_call_reaches_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _outside(tmp_path)
    messages, _ = _run(tmp_path, monkeypatch, folder, "allow:read", "t_folder_allow")
    assert "every workspace" in str(messages[1].content)
    assert "Quote 42" in str(messages[2].content)
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert f"COSCRIBE_EXTRA_READABLE_DIRS={folder.resolve()}" in env
    assert Environments(tmp_path / "state").thread_folders("t_folder_allow") == {}


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
