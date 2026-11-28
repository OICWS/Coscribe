"""Decision 0062 as tables: Auto mode's reviewer decides a command 0022 kept for the person,
a card's "allow similar" covers the calls like it for the rest of the conversation, and
Bypass mode approves every gated call while Settings allows it, under the same floor."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from coscribe.conversation import approval_scope
from coscribe.conversation.approval_scope import SimilarCall, similar_call
from coscribe.runtime_lg.audit import AuditLog
from coscribe.tools import ScheduledTrigger as _Trigger
from coscribe.tools.exec import commands as commands_module
from tests.test_approval_decisions import (
    COMMAND,
    LOCAL,
    _decide,
    _session,
    _Socket,
    _use_reviewer,
    _verdict,
    _write_exec_rule,
)


def _sandbox(monkeypatch: pytest.MonkeyPatch, sandboxed: bool) -> Counter[str]:
    """The sandbox's state, and the count of commands approved on the ground that it holds."""
    codex = Path("codex.exe") if sandboxed else None
    monkeypatch.setattr(approval_scope, "sandbox_codex", lambda state_dir: codex)
    monkeypatch.setattr(approval_scope, "sandbox_mode", lambda state_dir: "elevated")
    assumed: Counter[str] = Counter()
    monkeypatch.setattr(commands_module, "_SANDBOX_ASSUMED", assumed)
    return assumed


def _reasons(session: Any) -> list[str]:
    return [entry.reason for entry in AuditLog(session.settings.state_dir).read_all()]


@dataclass
class CommandRow:
    """A command without the sandbox in Auto mode, and what the reviewer's answer makes of it."""

    reply: str
    decision: str
    reasons: list[str]
    asked: bool = False


COMMAND_ROWS: dict[str, CommandRow] = {
    "the_reviewer_allows_it": CommandRow(_verdict("allow"), "approve", ["auto_review"]),
    "the_reviewer_blocks_it": CommandRow(_verdict("block"), "reject", ["auto_review_block"]),
    "no_answer_asks_the_person": CommandRow("not json", "approve", ["human"], asked=True),
}


@pytest.mark.parametrize("name", sorted(COMMAND_ROWS))
async def test_auto_mode_hands_an_unsandboxed_command_to_its_reviewer(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = COMMAND_ROWS[name]
    session = _session(tmp_path, monkeypatch)
    assumed = _sandbox(monkeypatch, sandboxed=False)
    reviewer = _use_reviewer(session, row.reply)
    socket = _Socket(True)

    result = await _decide(session, COMMAND, socket, answer=True, args={"command": "git status"})

    assert result["type"] == row.decision
    assert _reasons(session) == row.reasons
    request = str(reviewer.asked[0][-1].content)
    assert "outside any sandbox" in request
    cards = [e for e in socket.sent if e["type"] == "approval_required"]
    assert len(cards) == (1 if row.asked else 0)
    # Approved knowing it runs without the sandbox, so the command must not then require one.
    assert assumed[session.thread_id] == 0


@pytest.mark.parametrize("rule", ["exec_policy", "workspace"])
async def test_an_allow_rule_does_not_skip_the_reviewer_for_an_unsandboxed_command(
    rule: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    _sandbox(monkeypatch, sandboxed=False)
    reviewer = _use_reviewer(session, _verdict("block"))
    if rule == "exec_policy":
        _write_exec_rule(session, "allow")
    else:
        folder = Path(session.workspace_root)
        (folder / ".coscribe").mkdir(parents=True, exist_ok=True)
        rules = {"permissions": {"allow": [f"{COMMAND}(git *)"]}}
        (folder / ".coscribe" / "settings.json").write_text(json.dumps(rules), encoding="utf-8")
        session._assembly.workspace_folders.accept(folder)

    result = await _decide(session, COMMAND, _Socket(True), args={"command": "git push"})

    assert result["type"] == "reject"
    assert len(reviewer.asked) == 1
    assert _reasons(session) == ["auto_review_block"]


async def test_a_sandboxed_offline_command_still_counts_on_the_sandbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    assumed = _sandbox(monkeypatch, sandboxed=True)
    session.settings.allow_bypass_mode = True
    session._toggle_mode("bypass")

    await _decide(session, COMMAND, _Socket(True), args={"command": "git status"})

    assert assumed[session.thread_id] == 1


async def test_outside_auto_mode_the_person_still_approves_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    _sandbox(monkeypatch, sandboxed=False)
    session.preapproved_tools = frozenset({COMMAND})
    socket = _Socket(True)

    await _decide(session, COMMAND, socket, answer=True, args={"command": "git status"})

    [card] = [e for e in socket.sent if e["type"] == "approval_required"]
    assert card["asked_because"] == "command_unsandboxed"
    assert _reasons(session) == ["human"]


SIMILAR = {
    "git status": SimilarCall("run_background_command:git", "Allow git commands in this chat"),
    '"C:\\Program Files\\Git\\bin\\git.exe" log': SimilarCall(
        "run_background_command:git", "Allow git commands in this chat"
    ),
    "npm.cmd install": SimilarCall("run_background_command:npm", "Allow npm commands in this chat"),
    "git status && del notes.txt": None,
    "git log | more": None,
    "echo $(whoami)": None,
    "": None,
}


@pytest.mark.parametrize("command", sorted(SIMILAR))
def test_allow_similar_names_a_command_by_its_program(command: str) -> None:
    assert similar_call(COMMAND, {"command": command}) == SIMILAR[command]


def test_allow_similar_names_another_tool_by_itself_and_skips_the_code_module() -> None:
    expected = SimilarCall("send_email", "Allow send_email in this chat")
    assert similar_call("send_email", {"to": "a"}) == expected
    assert similar_call("run_code_command", {"command": "ls"}) is None


async def _answer_similar(session: Any, args: dict[str, Any], socket: _Socket) -> dict[str, Any]:
    """The decision, with its card answered "allow similar" the way the socket answers it."""
    request = {"name": COMMAND, "args": args}
    task = asyncio.create_task(session._decide_action_request(request, socket))
    while not task.done():
        for request_id, future in list(session._pending_approvals.items()):
            if not future.done():
                session.resolve_approval(request_id, True, "similar")
        await asyncio.sleep(0)
    return task.result()  # type: ignore[no-any-return]


async def test_a_card_allowed_similar_lets_the_same_program_through_for_the_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    _sandbox(monkeypatch, sandboxed=False)
    socket = _Socket(True)

    first = await asyncio.wait_for(_answer_similar(session, {"command": "git status"}, socket), 10)
    [card] = [e for e in socket.sent if e["type"] == "approval_required"]
    second = await _decide(session, COMMAND, socket, answer=False, args={"command": "git log"})
    other = await _decide(session, COMMAND, socket, answer=False, args={"command": "npm test"})

    assert card["allow_similar"] == "Allow git commands in this chat"
    assert (first["type"], second["type"], other["type"]) == ("approve", "approve", "reject")
    assert _reasons(session) == ["human", "allowed_similar", "human"]
    assert not session._similar_requests


@dataclass
class BypassRow:
    """A call in Bypass mode and what decides it."""

    tool: str = LOCAL
    args: dict[str, Any] = field(default_factory=lambda: {"path": "a.txt"})
    allowed: bool = True  # Settings' "Allow bypass permissions mode"
    exec_rule: str | None = None
    folder_rule: str | None = None
    run_mode: str | None = None
    decision: str = "approve"
    reasons: list[str] = field(default_factory=lambda: ["bypass"])


BYPASS_ROWS: dict[str, BypassRow] = {
    "a_delete": BypassRow(),
    "an_unsandboxed_command": BypassRow(COMMAND, {"command": "git push"}),
    "the_setting_turned_off_since": BypassRow(allowed=False, reasons=["human"]),
    "exec_policy_forbids_it": BypassRow(
        "run_python_script",
        {"script": "print(1)"},
        exec_rule="forbidden",
        decision="reject",
        reasons=["exec_policy"],
    ),
    "the_workspace_denies_it": BypassRow(
        folder_rule="deny", decision="reject", reasons=["workspace_settings"]
    ),
    "the_workspace_asks_for_it": BypassRow(folder_rule="ask", reasons=["human"]),
    "a_scheduled_run_keeps_its_tier": BypassRow(
        run_mode="manual", decision="reject", reasons=["unattended"]
    ),
}


@pytest.mark.parametrize("name", sorted(BYPASS_ROWS))
async def test_bypass_mode_approves_every_call_above_the_floor(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = BYPASS_ROWS[name]
    session = _session(tmp_path, monkeypatch)
    assumed = _sandbox(monkeypatch, sandboxed=False)
    session.settings.allow_bypass_mode = True
    session._toggle_mode("bypass")
    session.settings.allow_bypass_mode = row.allowed
    session.run_approval_mode = row.run_mode
    _write_exec_rule(session, row.exec_rule)
    if row.folder_rule is not None:
        folder = Path(session.workspace_root)
        (folder / ".coscribe").mkdir(parents=True, exist_ok=True)
        rules = {"permissions": {row.folder_rule: [row.tool]}}
        (folder / ".coscribe" / "settings.json").write_text(json.dumps(rules), encoding="utf-8")
        session._assembly.workspace_folders.accept(folder)
    attended = row.run_mode is None

    result = await _decide(session, row.tool, _Socket(attended), answer=True, args=row.args)

    assert result["type"] == row.decision
    assert _reasons(session) == row.reasons
    assert assumed[session.thread_id] == 0


def test_bypass_mode_comes_on_only_while_settings_allow_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)

    session._toggle_mode("bypass")
    refused = session.permission_mode
    session.settings.allow_bypass_mode = True
    session._toggle_mode("bypass")
    on = session.permission_mode
    session._toggle_mode("bypass")

    assert (refused, on, session.permission_mode) == ("manual", "bypass", "manual")


TIERS = {
    ("manual", False): "manual",
    ("auto", False): "auto",
    ("skip", False): "auto",
    ("skip", True): "skip",
    ("auto", True): "auto",
}


@pytest.mark.parametrize(("saved", "allowed"), sorted(TIERS))
def test_a_tasks_never_ask_tier_holds_only_while_settings_allow_bypass(
    saved: str, allowed: bool
) -> None:
    assert _Trigger.tier(saved, allowed) == TIERS[saved, allowed]


class _RunSession:
    """What a prompt run needs of its conversation, keeping the tier the turn ran under."""

    def __init__(self, allowed: bool) -> None:
        self.settings = type("S", (), {"allow_bypass_mode": allowed})()
        self.config: dict[str, Any] = {}
        self.ran_under: str | None = None
        self.active_run_prompt: str | None = None
        self.run_approval_mode: str | None = None
        state = type("State", (), {"tasks": []})()

        async def aget_state(config: Any) -> Any:
            return state

        self.lg_agent = type("Agent", (), {"aget_state": staticmethod(aget_state)})()

    async def handle_user_message(self, prompt: str, socket: Any) -> None:
        self.ran_under = self.run_approval_mode


@pytest.mark.parametrize("allowed", [False, True])
async def test_a_prompt_run_takes_its_tier_through_the_setting(
    allowed: bool, tmp_path: Path
) -> None:
    from datetime import datetime

    from coscribe.runtime_lg import scheduled_tasks
    from coscribe.tools import ScheduledRun, ScheduledTrigger
    from coscribe.tools.bookkeeping.scheduled_tasks import ScheduleRule

    trigger = ScheduledTrigger(
        trigger_id="t",
        name="Task",
        schedule=ScheduleRule(kind="manual", at=""),
        enabled=True,
        created_at=datetime.now().isoformat(),
        next_run_at=None,
        prompt="Do it",
        approval_mode="skip",
    )
    run = ScheduledRun(
        run_id="r", thread_id="th", started_at=datetime.now().isoformat(), source="manual"
    )
    session = _RunSession(allowed)

    status = await scheduled_tasks._run_in_session(trigger, run, "", session)

    assert status == ("completed", None)
    assert session.ran_under == ("skip" if allowed else "auto")
    assert session.run_approval_mode is None
