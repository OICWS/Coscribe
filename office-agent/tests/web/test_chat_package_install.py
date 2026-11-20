# ruff: noqa: E402
"""Web tests: a script's missing package installed from the chat (decision 0056)."""

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage, ToolMessage

from coscribe.conversation import package_install
from coscribe.runtime_lg import AuditLog

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _receive_until,
    _tool_call,
)


class _FakeEnv:
    """script-env as the installer and the lister see it, without pip."""

    def __init__(self, installed: dict[str, str] | None = None, error: str | None = None) -> None:
        self.installed = dict(installed or {})
        self.error = error
        self.installs: list[str] = []

    def install(self, _state_dir: Any, package: str) -> dict[str, object]:
        self.installs.append(package)
        if self.error:
            return {"success": False, "error": self.error}
        name, _, version = package.partition("==")
        self.installed[name] = version or "1.0.0"
        return {"success": True, "error": None}

    def listing(self, _state_dir: Any) -> list[dict[str, str]]:
        return [{"name": n, "version": v} for n, v in self.installed.items()]


def _patch(monkeypatch: pytest.MonkeyPatch, env: _FakeEnv) -> None:
    monkeypatch.setattr(package_install, "install_python_package", env.install)
    monkeypatch.setattr(package_install, "list_python_packages", env.listing)


def _call(call_id: str, package: str, runtime: str = "python") -> AIMessage:
    args = {"runtime": runtime, "package": package, "reason": "to read the .msg emails"}
    return AIMessage(content="", tool_calls=[_tool_call(call_id, "install_package", args)])


def _run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    responses: list[AIMessage],
    answers: list[str],
    thread: str,
) -> tuple[list[ToolMessage], list[dict[str, Any]]]:
    """Answers each card in turn; returns the tool results and every event after the cards."""
    monkeypatch.chdir(tmp_path)
    fake_model = FakeToolCallingChatModel(responses=[*responses, AIMessage(content="done")])
    events: list[dict[str, Any]] = []
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect(f"/ws/{thread}") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "read the emails"})
            for answer in answers:
                card = _receive_until(ws, "package_install_required")[-1]
                events.append(card)
                ws.send_json({"type": "question_response", "id": card["id"], "answer": answer})
            events.extend(_receive_until(ws, "agent_message"))
    tool_messages = [m for m in fake_model.received[-1] if isinstance(m, ToolMessage)]
    return tool_messages, events


def test_install_runs_the_installer_and_tells_the_card_and_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _FakeEnv()
    _patch(monkeypatch, env)
    messages, events = _run(
        tmp_path, monkeypatch, [_call("c1", "extract-msg==0.48.0")], ["install"], "t_pkg_install"
    )
    card = events[0]
    assert (card["runtime"], card["package"], card["name"]) == (
        "python",
        "extract-msg==0.48.0",
        "extract-msg",
    )
    assert card["reason"] == "to read the .msg emails"
    assert env.installs == ["extract-msg==0.48.0"]
    [finished] = [e for e in events if e["type"] == "package_install_finished"]
    assert finished == {
        "type": "package_install_finished",
        "id": card["id"],
        "installed": True,
        "version": "0.48.0",
    }
    assert "Installed extract-msg 0.48.0" in str(messages[0].content)
    audit = AuditLog(tmp_path / "state").read_all()
    [entry] = [e for e in audit if e.tool_name == "install_package"]
    assert (entry.decision, entry.reason, entry.detail) == ("approve", "human", "installed")


def test_a_failed_install_shows_the_installers_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _FakeEnv(error="ERROR: No matching distribution found for extract-mgs")
    _patch(monkeypatch, env)
    messages, events = _run(
        tmp_path, monkeypatch, [_call("c1", "extract-mgs")], ["install"], "t_pkg_failed"
    )
    [finished] = [e for e in events if e["type"] == "package_install_finished"]
    assert finished["installed"] is False
    assert "No matching distribution" in finished["error"]
    assert "failed" in str(messages[0].content)


def test_not_now_holds_for_the_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _FakeEnv()
    _patch(monkeypatch, env)
    messages, events = _run(
        tmp_path,
        monkeypatch,
        [_call("c1", "extract-msg"), _call("c2", "Extract_Msg")],
        ["decline"],
        "t_pkg_decline",
    )
    assert env.installs == []
    assert len([e for e in events if e["type"] == "package_install_required"]) == 1
    assert "chose not to install" in str(messages[0].content)
    assert "already declined" in str(messages[1].content)


def test_an_installed_package_needs_no_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = _FakeEnv(installed={"openpyxl": "3.1.2"})
    _patch(monkeypatch, env)
    messages, _ = _run(tmp_path, monkeypatch, [_call("c1", "openpyxl")], [], "t_pkg_have")
    assert env.installs == []
    assert "openpyxl 3.1.2 is already installed" in str(messages[0].content)


@pytest.mark.parametrize(
    "package",
    [
        "https://example.com/evil.whl",
        "git+https://github.com/x/y",
        "--index-url=https://evil.example/simple",
        "-r requirements.txt",
        "numpy pandas",
        "./local_folder",
        "C:\\wheels\\x.whl",
    ],
)
def test_anything_but_one_name_is_refused_before_a_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, package: str
) -> None:
    env = _FakeEnv()
    _patch(monkeypatch, env)
    messages, _ = _run(tmp_path, monkeypatch, [_call("c1", package)], [], "t_pkg_bad")
    assert env.installs == []
    assert "is not one package name" in str(messages[0].content)


@pytest.mark.parametrize(
    ("runtime", "package", "parsed"),
    [
        ("python", "openpyxl", ("openpyxl", None)),
        ("python", "openpyxl==3.1.2", ("openpyxl", "3.1.2")),
        ("python", "pandas>=2", ("pandas", None)),
        ("python", "requests[socks]", ("requests", None)),
        ("node", "sharp", ("sharp", None)),
        ("node", "sharp@0.33.5", ("sharp", "0.33.5")),
        ("node", "@napi-rs/canvas@^0.1", ("@napi-rs/canvas", "^0.1")),
        ("node", "Sharp", None),
        ("node", "github:user/repo", None),
        ("ruby", "rails", None),
    ],
)
def test_parse_spec(runtime: str, package: str, parsed: tuple[str, str | None] | None) -> None:
    assert package_install.parse_spec(runtime, package) == parsed
