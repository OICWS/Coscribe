"""What a conversation decides about one gated tool call, as a table.

`ChatSessionLG._decide_action_request` decides what runs without asking, so before it is
split (the scale assessment, section 4) every combination that changes its answer is
written down here. `ROWS` holds the precedence of a stop, a hook veto, an exec-policy rule,
plan mode, the standing approvals (pre-approved, Accept Edits, a scheduled run's tier) and,
last, asking a person or refusing because nobody is there. `AUTO_ROWS` holds Auto mode's
reviewer and the pause after its blocks, `CODE_ROWS` the code module's allowances for a
sub-agent, and `QUESTION_ROWS` the tools that answer with "respond" instead of "reject".
Each row is run through the real method with a fake socket; the decision, the audit record
and whether the call was announced are all checked. A row changes only when the decision it
names is changed on purpose.
"""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langgraph.checkpoint.memory import InMemorySaver

from coscribe.code_runtime import CodePermissions
from coscribe.config import Settings
from coscribe.conversation import session as session_module
from coscribe.conversation.session import ChatSessionLG, _SubAgentApprovalChannel
from coscribe.runtime import empty_hooks_config
from coscribe.runtime_lg.audit import AuditLog
from coscribe.runtime_lg.auto_review import Verdict
from coscribe.tools.subagent_tasks import SubAgentTask

from .wire_check import check_event

READ, LOCAL, EXEC, EXTERNAL = "read_file", "write_file", "run_python_script", "send_email"
CODE_COMMAND, CODE_CHANGE = "run_code_command", "apply_code_change"
RISKS = {
    LOCAL: "WRITE_LOCAL",
    EXEC: "EXEC",
    EXTERNAL: "EXTERNAL",
    CODE_COMMAND: "EXEC",
    CODE_CHANGE: "WRITE_LOCAL",
}


class _Model(BaseChatModel):
    def bind_tools(self, tools: Any, *, tool_choice: str | None = None, **kwargs: Any) -> Any:
        return self

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        raise AssertionError("a decision never calls the model")

    @property
    def _llm_type(self) -> str:
        return "unused"


class _ContextWindow:
    def get_context_window(self, model: str) -> int:
        return 128000


class _Socket:
    """A client connection; `can_resolve_approvals = False` is an unattended run."""

    def __init__(self, attended: bool) -> None:
        self.can_resolve_approvals = attended
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, data: dict[str, Any]) -> None:
        check_event(data)
        self.sent.append(data)


def _session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ChatSessionLG:
    monkeypatch.setattr(
        session_module, "resolve_chat_model", lambda name, custom_providers=None: _Model()
    )
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        default_model="fake:model",
        workspace_root=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        skills_dir=tmp_path / "skills",
        memory_path=tmp_path / "MEMORY.md",
        auto_title_threads=False,
        default_permission_mode="manual",
        exec_policy_path=tmp_path / "exec_policy.json",
    )
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    session = ChatSessionLG(
        thread_id="t1",
        settings=settings,
        context_window_client=_ContextWindow(),
        custom_providers={},
        extra_tools=[],
        checkpointer=InMemorySaver(),
        hooks_config=empty_hooks_config(),
        enabled_skill_names=set(),
        workspace_root=tmp_path / "workspace",
    )
    session._gated_tool_risks = dict(RISKS)
    return session


@dataclass
class Row:
    """One situation and what the conversation decides in it."""

    tool: str
    decision: str
    reason: str | None  # the audit record's reason; None when nothing is logged
    stop: bool = False
    veto: str | None = None
    exec_rule: str | None = None  # "forbidden", "allow", "prompt" for the script's text
    plan: bool = False
    preapproved: bool = False
    accept_edits: bool = False
    run_mode: str | None = None  # a scheduled run's approval tier: "skip" or "auto"
    attended: bool = True
    human: bool | None = None  # the person's answer, when the conversation asks
    announced: bool = False  # a `tool_started` message goes to the client
    asked: bool = False  # an `approval_required` message goes to the client


ROWS: dict[str, Row] = {
    # -- a stop request and a hook veto come first, whatever else is set
    "stop_before_everything": Row(LOCAL, "reject", None, stop=True, preapproved=True),
    "veto_on_a_tool_that_is_not_gated": Row(READ, "reject", "hook_veto", veto="no reading"),
    "veto_beats_preapproved": Row(LOCAL, "reject", "hook_veto", veto="no", preapproved=True),
    "veto_beats_a_run_that_skips_approval": Row(
        EXEC, "reject", "hook_veto", veto="no", run_mode="skip"
    ),
    # -- a tool that is not gated is approved, plan mode or not
    "not_gated": Row(READ, "approve", None),
    "not_gated_in_plan_mode": Row(READ, "approve", None, plan=True),
    # -- plan mode refuses every gated call, and the standing approvals do not lift it
    "plan_refuses_a_gated_call": Row(LOCAL, "reject", "plan_mode", plan=True),
    "plan_beats_preapproved": Row(LOCAL, "reject", "plan_mode", plan=True, preapproved=True),
    "plan_beats_accept_edits": Row(LOCAL, "reject", "plan_mode", plan=True, accept_edits=True),
    "plan_beats_a_run_that_skips_approval": Row(
        EXEC, "reject", "plan_mode", plan=True, run_mode="skip"
    ),
    # -- the exec policy applies to scripts only, and "forbidden" comes before plan mode
    "exec_forbidden": Row(EXEC, "reject", "exec_policy", exec_rule="forbidden"),
    "exec_forbidden_beats_plan_mode": Row(
        EXEC, "reject", "exec_policy", exec_rule="forbidden", plan=True
    ),
    "exec_forbidden_beats_preapproved": Row(
        EXEC, "reject", "exec_policy", exec_rule="forbidden", preapproved=True
    ),
    "exec_forbidden_beats_a_run_that_skips_approval": Row(
        EXEC, "reject", "exec_policy", exec_rule="forbidden", run_mode="skip"
    ),
    "exec_allow": Row(EXEC, "approve", "exec_policy", exec_rule="allow", announced=True),
    "exec_allow_does_not_lift_plan_mode": Row(
        EXEC, "reject", "plan_mode", exec_rule="allow", plan=True
    ),
    "exec_allow_works_unattended": Row(
        EXEC, "approve", "exec_policy", exec_rule="allow", attended=False, announced=True
    ),
    "exec_prompt_rule_still_asks": Row(
        EXEC, "approve", "human", exec_rule="prompt", human=True, asked=True
    ),
    "a_rule_for_scripts_is_ignored_for_other_tools": Row(
        LOCAL, "approve", "human", exec_rule="forbidden", human=True, asked=True
    ),
    # -- standing approvals, with the reason each one is logged under
    "preapproved": Row(LOCAL, "approve", "preapproved", preapproved=True, announced=True),
    "preapproved_covers_every_risk": Row(
        EXTERNAL, "approve", "preapproved", preapproved=True, announced=True
    ),
    "preapproved_works_unattended": Row(
        EXEC, "approve", "preapproved", preapproved=True, attended=False, announced=True
    ),
    "preapproved_is_logged_before_accept_edits": Row(
        LOCAL, "approve", "preapproved", preapproved=True, accept_edits=True, announced=True
    ),
    "accept_edits_approves_a_local_write": Row(
        LOCAL, "approve", "accept_edits", accept_edits=True, announced=True
    ),
    "accept_edits_still_asks_for_a_script": Row(
        EXEC, "approve", "human", accept_edits=True, human=True, asked=True
    ),
    "accept_edits_still_asks_for_an_external_action": Row(
        EXTERNAL, "reject", "human", accept_edits=True, human=False, asked=True
    ),
    "a_run_that_skips_approval_approves_every_risk": Row(
        EXEC, "approve", "approval_mode_skip", run_mode="skip", announced=True
    ),
    "a_run_that_skips_approval_works_unattended": Row(
        EXTERNAL, "approve", "approval_mode_skip", run_mode="skip", attended=False, announced=True
    ),
    "a_run_in_auto_approves_a_local_write": Row(
        LOCAL, "approve", "approval_mode_auto", run_mode="auto", announced=True
    ),
    "a_run_in_auto_still_asks_for_a_script": Row(
        EXEC, "reject", "human", run_mode="auto", human=False, asked=True
    ),
    "a_run_in_auto_refuses_a_script_when_nobody_is_there": Row(
        EXEC, "reject", "unattended", run_mode="auto", attended=False
    ),
    # -- nothing decided it: ask a person, or refuse when nobody can answer
    "ask_and_the_person_approves": Row(LOCAL, "approve", "human", human=True, asked=True),
    "ask_and_the_person_refuses": Row(LOCAL, "reject", "human", human=False, asked=True),
    "unattended_refuses_instead_of_waiting": Row(LOCAL, "reject", "unattended", attended=False),
}


async def _decide(
    session: ChatSessionLG,
    tool: str,
    socket: Any,
    *,
    answer: Any = None,
    args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the decision and answer whatever it asks: an approval card with `bool(answer)`
    (a refusal when the row has no answer, so a decision that asks by mistake fails the
    assertions instead of hanging), a question or plan or draft with `answer` itself."""
    request = {
        "name": tool,
        "args": copy.deepcopy(args)
        if args is not None
        else {"script": "print(1)", "path": "a.txt"},
    }

    async def run() -> dict[str, Any]:
        task = asyncio.create_task(session._decide_action_request(request, socket))
        while not task.done():
            for future in list(session._pending_approvals.values()):
                if not future.done():
                    future.set_result(bool(answer))
            for future in list(session._pending_questions.values()):
                if not future.done():
                    future.set_result(answer)
            await asyncio.sleep(0)
        return task.result()  # type: ignore[no-any-return]

    return await asyncio.wait_for(run(), timeout=10)


def _write_exec_rule(session: ChatSessionLG, decision: str | None) -> None:
    if decision is None:
        return
    rules = [{"pattern": ".", "decision": decision, "justification": "by the policy"}]
    session.settings.exec_policy_path.write_text(  # type: ignore[union-attr]
        json.dumps({"rules": rules}), encoding="utf-8"
    )


def _veto(monkeypatch: pytest.MonkeyPatch, session: ChatSessionLG, reason: str | None) -> None:
    async def veto(tool: str, args: dict[str, Any]) -> str | None:
        return reason

    monkeypatch.setattr(session, "_run_pre_tool_use_hooks", veto)


def _sent(socket: _Socket, kind: str) -> int:
    return sum(1 for message in socket.sent if message["type"] == kind)


@pytest.mark.parametrize("name", sorted(ROWS))
async def test_the_decision_for_one_situation(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = ROWS[name]
    session = _session(tmp_path, monkeypatch)
    session._stop_requested = row.stop
    session.plan_mode = row.plan
    session.accept_edits = row.accept_edits
    session.run_approval_mode = row.run_mode
    session.preapproved_tools = frozenset({row.tool}) if row.preapproved else frozenset()
    _write_exec_rule(session, row.exec_rule)
    _veto(monkeypatch, session, row.veto)
    socket = _Socket(row.attended)

    result = await _decide(session, row.tool, socket, answer=row.human)

    assert result["type"] == row.decision
    logged = AuditLog(session.settings.state_dir).read_all()
    assert [entry.reason for entry in logged] == ([row.reason] if row.reason else [])
    assert [entry.decision for entry in logged] == ([row.decision] if row.reason else [])
    sent = [message["type"] for message in socket.sent]
    assert ("tool_started" in sent) is row.announced
    assert ("approval_required" in sent) is row.asked
    assert not session._pending_approvals


async def test_a_refusal_carries_the_reason_the_model_is_told(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    session.plan_mode = True
    session.settings.exec_policy_path.write_text(  # type: ignore[union-attr]
        json.dumps({"rules": [{"pattern": ".", "decision": "forbidden", "justification": "no"}]}),
        encoding="utf-8",
    )
    socket = _Socket(attended=True)
    request = {"name": LOCAL, "args": {}}

    plan = await session._decide_action_request(request, socket)
    script = await session._decide_action_request({"name": EXEC, "args": {"script": "x"}}, socket)

    assert "Plan mode is active" in plan["message"]
    assert script == {"type": "reject", "message": "no"}


# ---------------------------------------------------------------------------
# Auto mode: a reviewer model decides what the standing approvals did not
# ---------------------------------------------------------------------------

REASON = "it only touches the folder"


@dataclass
class AutoRow:
    """One situation under Auto mode: what the reviewer says and what follows."""

    tool: str
    decision: str
    reasons: list[str]  # the audit records' reasons, in order
    reviewer: str = "silent"  # "allow", "block" or "silent" (no answer)
    in_row: int = 0  # blocks in a row before the call
    total: int = 0  # blocks in all before the call
    paused: bool = False
    auto_mode: bool = True
    plan: bool = False
    preapproved: bool = False
    accept_edits: bool = False
    exec_rule: str | None = None
    veto: str | None = None
    run_mode: str | None = None
    attended: bool = True
    human: bool | None = None
    consulted: bool = False  # the reviewer is asked
    announced: bool = False
    asked: bool = False
    note: str | None = None  # a part of the reviewer's note on the approval card
    message: str | None = None  # a part of the refusal the model reads
    in_row_after: int | None = None  # None: unchanged
    total_after: int | None = None
    paused_after: bool | None = None


AUTO_ROWS: dict[str, AutoRow] = {
    # -- the reviewer's answer
    "reviewer_allows": AutoRow(
        LOCAL, "approve", ["auto_review"], "allow", consulted=True, announced=True
    ),
    "reviewer_allows_any_risk": AutoRow(
        EXTERNAL, "approve", ["auto_review"], "allow", consulted=True, announced=True
    ),
    "an_allow_ends_the_run_of_blocks_but_not_the_total": AutoRow(
        LOCAL,
        "approve",
        ["auto_review"],
        "allow",
        in_row=2,
        total=5,
        consulted=True,
        announced=True,
        in_row_after=0,
        total_after=5,
    ),
    "reviewer_blocks": AutoRow(
        LOCAL,
        "reject",
        ["auto_review_block"],
        "block",
        consulted=True,
        message=f"Auto mode blocked this: {REASON}",
        in_row_after=1,
        total_after=1,
    ),
    "a_second_block_in_a_row_still_refuses": AutoRow(
        LOCAL,
        "reject",
        ["auto_review_block"],
        "block",
        in_row=1,
        total=1,
        consulted=True,
        in_row_after=2,
        total_after=2,
    ),
    "no_answer_from_the_reviewer_asks_a_person": AutoRow(
        LOCAL,
        "approve",
        ["human"],
        consulted=True,
        human=True,
        asked=True,
        note="gave no answer",
        in_row=2,
        total=7,
    ),
    # -- three blocks in a row, or twenty in all, pause Auto mode and ask
    "the_third_block_in_a_row_pauses_and_asks": AutoRow(
        LOCAL,
        "reject",
        ["auto_review_block", "human"],
        "block",
        in_row=2,
        total=2,
        consulted=True,
        human=False,
        asked=True,
        note=f"kept blocking actions, so it's asking you: {REASON}",
        in_row_after=3,
        total_after=3,
        paused_after=True,
    ),
    "approving_after_the_pause_resumes_auto_mode": AutoRow(
        LOCAL,
        "approve",
        ["auto_review_block", "human"],
        "block",
        in_row=2,
        total=2,
        consulted=True,
        human=True,
        asked=True,
        note="kept blocking actions",
        in_row_after=0,
        total_after=3,
        paused_after=False,
    ),
    "the_nineteenth_block_in_all_still_refuses": AutoRow(
        LOCAL,
        "reject",
        ["auto_review_block"],
        "block",
        in_row=0,
        total=18,
        consulted=True,
        in_row_after=1,
        total_after=19,
    ),
    "the_twentieth_block_in_all_pauses_and_restarts_the_count": AutoRow(
        LOCAL,
        "reject",
        ["auto_review_block", "human"],
        "block",
        in_row=0,
        total=19,
        consulted=True,
        human=False,
        asked=True,
        note="kept blocking actions",
        in_row_after=1,
        total_after=0,
        paused_after=True,
    ),
    "a_paused_auto_mode_asks_without_the_reviewer": AutoRow(
        LOCAL,
        "approve",
        ["human"],
        "allow",
        paused=True,
        in_row=3,
        human=True,
        asked=True,
        in_row_after=0,
        paused_after=False,
    ),
    "auto_mode_off_asks_without_the_reviewer": AutoRow(
        LOCAL, "approve", ["human"], "allow", auto_mode=False, human=True, asked=True
    ),
    # -- the reviewer comes after everything that decides without it
    "preapproved_comes_before_the_reviewer": AutoRow(
        LOCAL, "approve", ["preapproved"], "block", preapproved=True, announced=True
    ),
    "accept_edits_comes_before_the_reviewer": AutoRow(
        LOCAL, "approve", ["accept_edits"], "block", accept_edits=True, announced=True
    ),
    "plan_mode_comes_before_the_reviewer": AutoRow(
        LOCAL, "reject", ["plan_mode"], "allow", plan=True
    ),
    "exec_forbidden_comes_before_the_reviewer": AutoRow(
        EXEC, "reject", ["exec_policy"], "allow", exec_rule="forbidden"
    ),
    "exec_allow_comes_before_the_reviewer": AutoRow(
        EXEC, "approve", ["exec_policy"], "block", exec_rule="allow", announced=True
    ),
    "a_hook_veto_comes_before_the_reviewer": AutoRow(
        LOCAL, "reject", ["hook_veto"], "allow", veto="no"
    ),
    "a_scheduled_run_keeps_its_own_tier_and_skips_the_reviewer": AutoRow(
        EXEC, "reject", ["human"], "allow", run_mode="auto", human=False, asked=True
    ),
    # -- nobody is there: the reviewer still answers, and a refusal is the last resort
    "reviewer_allows_when_unattended": AutoRow(
        EXEC, "approve", ["auto_review"], "allow", attended=False, consulted=True, announced=True
    ),
    "reviewer_blocks_when_unattended": AutoRow(
        EXEC,
        "reject",
        ["auto_review_block"],
        "block",
        attended=False,
        consulted=True,
        message="Auto mode blocked this",
        in_row_after=1,
        total_after=1,
    ),
    "the_third_block_unattended_pauses_and_refuses": AutoRow(
        EXEC,
        "reject",
        ["auto_review_block", "unattended"],
        "block",
        in_row=2,
        total=2,
        attended=False,
        consulted=True,
        message="No one is available to approve this",
        in_row_after=3,
        total_after=3,
        paused_after=True,
    ),
    "no_answer_unattended_refuses": AutoRow(
        EXEC,
        "reject",
        ["unattended"],
        attended=False,
        consulted=True,
        message="No one is available to approve this",
    ),
}


@pytest.mark.parametrize("name", sorted(AUTO_ROWS))
async def test_the_decision_under_auto_mode(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = AUTO_ROWS[name]
    session = _session(tmp_path, monkeypatch)
    session.auto_mode = row.auto_mode
    session.plan_mode = row.plan
    session.accept_edits = row.accept_edits
    session.run_approval_mode = row.run_mode
    session.preapproved_tools = frozenset({row.tool}) if row.preapproved else frozenset()
    session._auto_paused = row.paused
    session._auto_blocks_in_row = row.in_row
    session._auto_blocks_total = row.total
    _write_exec_rule(session, row.exec_rule)
    _veto(monkeypatch, session, row.veto)
    verdicts = {
        "allow": Verdict(True, REASON),
        "block": Verdict(False, REASON),
        "silent": None,
    }
    asked_reviewer: list[str] = []

    async def reviewer(
        tool: str, args: dict[str, Any], *, delegated_task: str = ""
    ) -> Verdict | None:
        asked_reviewer.append(tool)
        return verdicts[row.reviewer]

    monkeypatch.setattr(session, "_auto_review", reviewer)
    socket = _Socket(row.attended)

    result = await _decide(session, row.tool, socket, answer=row.human)

    assert result["type"] == row.decision
    if row.message is not None:
        assert row.message in result["message"]
    logged = AuditLog(session.settings.state_dir).read_all()
    assert [entry.reason for entry in logged] == row.reasons
    assert bool(asked_reviewer) is row.consulted
    assert _sent(socket, "tool_started") == (1 if row.announced else 0)
    cards = [m for m in socket.sent if m["type"] == "approval_required"]
    assert len(cards) == (1 if row.asked else 0)
    if row.note is not None:
        assert row.note in cards[0]["reviewer_note"]
    elif cards:
        assert cards[0]["reviewer_note"] is None
    assert session._auto_blocks_in_row == (
        row.in_row if row.in_row_after is None else row.in_row_after
    )
    assert session._auto_blocks_total == (row.total if row.total_after is None else row.total_after)
    assert session._auto_paused is (row.paused if row.paused_after is None else row.paused_after)
    assert not session._pending_approvals


# ---------------------------------------------------------------------------
# The code module's allowances for a sub-agent's commands and file changes
# ---------------------------------------------------------------------------


@dataclass
class CodeRow:
    """One code-module call from a sub-agent task and whether it needs a card."""

    tool: str
    decision: str
    reasons: list[str]
    channel: bool = True  # the call comes from a sub-agent task (not the conversation itself)
    task_allows: tuple[str, str] | None = None  # (task id, tool) allowed on an earlier card
    setting: str = "ask"  # Settings > Code for this tool: "ask" or "allow"
    attended: bool = True
    run_mode: str | None = None
    plan: bool = False
    preapproved: bool = False
    veto: str | None = None
    human: bool | None = None
    announced: bool = False
    asked: bool = False


CODE_ROWS: dict[str, CodeRow] = {
    "ask_by_default": CodeRow(CODE_COMMAND, "approve", ["human"], human=True, asked=True),
    "a_card_the_person_refuses": CodeRow(CODE_CHANGE, "reject", ["human"], human=False, asked=True),
    "an_earlier_card_allowed_this_tool_for_this_task": CodeRow(
        CODE_COMMAND,
        "approve",
        ["code_allowed"],
        task_allows=("task-1", CODE_COMMAND),
        announced=True,
    ),
    "an_earlier_card_for_another_task_does_not_count": CodeRow(
        CODE_COMMAND,
        "approve",
        ["human"],
        task_allows=("task-2", CODE_COMMAND),
        human=True,
        asked=True,
    ),
    "an_earlier_card_for_another_tool_does_not_count": CodeRow(
        CODE_COMMAND,
        "approve",
        ["human"],
        task_allows=("task-1", CODE_CHANGE),
        human=True,
        asked=True,
    ),
    "a_task_allowance_works_unattended": CodeRow(
        CODE_CHANGE,
        "approve",
        ["code_allowed"],
        task_allows=("task-1", CODE_CHANGE),
        attended=False,
        announced=True,
    ),
    "the_setting_allows_a_command": CodeRow(
        CODE_COMMAND, "approve", ["code_allowed"], setting="allow", announced=True
    ),
    "the_setting_allows_a_file_change": CodeRow(
        CODE_CHANGE, "approve", ["code_allowed"], setting="allow", announced=True
    ),
    "the_setting_does_not_reach_an_unattended_turn": CodeRow(
        CODE_COMMAND, "reject", ["unattended"], setting="allow", attended=False
    ),
    "the_setting_does_not_reach_a_run_that_asks": CodeRow(
        CODE_COMMAND, "reject", ["human"], setting="allow", run_mode="auto", human=False, asked=True
    ),
    "a_run_that_skips_approval_decides_before_the_setting_is_read": CodeRow(
        CODE_COMMAND,
        "approve",
        ["approval_mode_skip"],
        setting="allow",
        run_mode="skip",
        announced=True,
    ),
    "the_setting_does_not_reach_the_conversation_itself": CodeRow(
        CODE_COMMAND, "approve", ["human"], channel=False, setting="allow", human=True, asked=True
    ),
    "a_task_allowance_needs_a_sub_agent_too": CodeRow(
        CODE_COMMAND,
        "approve",
        ["human"],
        channel=False,
        task_allows=("task-1", CODE_COMMAND),
        human=True,
        asked=True,
    ),
    "the_setting_does_not_cover_other_tools": CodeRow(
        LOCAL, "approve", ["human"], setting="allow", human=True, asked=True
    ),
    "code_allowed_is_logged_before_preapproved": CodeRow(
        CODE_COMMAND, "approve", ["code_allowed"], setting="allow", preapproved=True, announced=True
    ),
    "plan_mode_beats_the_setting": CodeRow(
        CODE_COMMAND, "reject", ["plan_mode"], setting="allow", plan=True
    ),
    "plan_mode_beats_a_task_allowance": CodeRow(
        CODE_CHANGE, "reject", ["plan_mode"], task_allows=("task-1", CODE_CHANGE), plan=True
    ),
    "a_hook_veto_beats_the_setting": CodeRow(
        CODE_COMMAND, "reject", ["hook_veto"], setting="allow", veto="no"
    ),
}


@pytest.mark.parametrize("name", sorted(CODE_ROWS))
async def test_the_decision_for_a_code_module_call(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = CODE_ROWS[name]
    session = _session(tmp_path, monkeypatch)
    session.plan_mode = row.plan
    session.run_approval_mode = row.run_mode
    session.preapproved_tools = frozenset({row.tool}) if row.preapproved else frozenset()
    if row.task_allows is not None:
        session._code_task_allowances.add(row.task_allows)
    if row.setting == "allow":
        CodePermissions(session.settings.state_dir, (CODE_COMMAND, CODE_CHANGE)).update(
            {CODE_COMMAND: "allow", CODE_CHANGE: "allow"}
        )
    _veto(monkeypatch, session, row.veto)
    socket = _Socket(row.attended)
    session._turn_websocket = socket
    task = SubAgentTask(
        task_id="task-1",
        thread_id="t1",
        instructions="",
        prompt="do it",
        tool_names="",
        description="a code task",
        status="running",
        started_at="2026-10-13T00:00:00Z",
    )
    channel = _SubAgentApprovalChannel(session, task) if row.channel else socket
    announced: list[str] = []

    async def announce(tool: str, args: dict[str, Any], websocket: Any) -> None:
        announced.append(tool)

    # A sub-agent's channel forwards approval cards only, so the announcement is watched here.
    monkeypatch.setattr(session, "_send_tool_started", announce)

    result = await _decide(session, row.tool, channel, answer=row.human)

    assert result["type"] == row.decision
    logged = AuditLog(session.settings.state_dir).read_all()
    assert [entry.reason for entry in logged] == row.reasons
    assert len(announced) == (1 if row.announced else 0)
    assert _sent(socket, "approval_required") == (1 if row.asked else 0)
    assert not session._pending_approvals
    assert not session._code_requests
    assert not session._subagent_request_ids


# ---------------------------------------------------------------------------
# The question, plan and task-draft tools answer with "respond", never "reject"
# ---------------------------------------------------------------------------

ASK, PLAN, CREATE_TASK, EDIT_TASK = (
    "ask_user_question",
    "exit_plan_mode",
    "create_scheduled_task",
    "edit_scheduled_task",
)
NO_ONE_QUESTION = "No one is available to answer this question"
NO_ONE_DRAFT = "No one is available to review this draft"


@dataclass
class QuestionRow:
    """One call to a tool that asks the person something and what it answers."""

    tool: str
    message: str  # a part of the answer the model reads
    reasons: list[str] = field(default_factory=list)  # the audit records' reasons
    stop: bool = False
    veto: str | None = None
    plan: bool = False
    attended: bool = True
    answer: str | list[str | None] | None = None  # what the person types or clicks
    args: dict[str, Any] = field(default_factory=dict)
    sent: str | None = None  # the message type the client receives, if any
    plan_after: bool = False
    auto_after: bool = False
    exec_rule: str | None = None


ONE_QUESTION = {"questions": [{"question": "Which file?", "options": ["a.txt", "b.txt"]}]}

QUESTION_ROWS: dict[str, QuestionRow] = {
    # -- the person's answer is the tool's result
    "a_question_is_answered": QuestionRow(
        ASK, "b.txt", answer=["b.txt"], args=ONE_QUESTION, sent="question_required"
    ),
    "a_skipped_question_says_so": QuestionRow(
        ASK, "(skipped)", answer=[None], args=ONE_QUESTION, sent="question_required"
    ),
    "closed_questions_say_so": QuestionRow(
        ASK, "closed the questions", answer=None, args=ONE_QUESTION, sent="question_required"
    ),
    "a_question_is_not_blocked_by_plan_mode": QuestionRow(
        ASK,
        "a.txt",
        plan=True,
        answer=["a.txt"],
        args=ONE_QUESTION,
        sent="question_required",
        plan_after=True,
    ),
    "a_question_is_not_blocked_by_an_exec_rule": QuestionRow(
        ASK,
        "a.txt",
        answer=["a.txt"],
        args=ONE_QUESTION,
        sent="question_required",
        exec_rule="forbidden",
    ),
    # -- a stop, a veto and an unattended run answer instead of asking
    "a_stop_answers_a_question": QuestionRow(ASK, "Stopped by user.", stop=True, args=ONE_QUESTION),
    "a_stop_answers_a_plan": QuestionRow(PLAN, "Stopped by user.", stop=True),
    "a_stop_answers_a_draft": QuestionRow(CREATE_TASK, "Stopped by user.", stop=True),
    "a_hook_veto_answers_a_question": QuestionRow(
        ASK, "no asking", reasons=["hook_veto"], veto="no asking", args=ONE_QUESTION
    ),
    "a_hook_veto_answers_a_plan": QuestionRow(
        PLAN, "no plans", reasons=["hook_veto"], veto="no plans"
    ),
    "a_hook_veto_answers_a_draft": QuestionRow(
        EDIT_TASK, "no tasks", reasons=["hook_veto"], veto="no tasks"
    ),
    "unattended_answers_a_question": QuestionRow(
        ASK, NO_ONE_QUESTION, reasons=["unattended"], attended=False, args=ONE_QUESTION
    ),
    "unattended_answers_a_plan": QuestionRow(
        PLAN, NO_ONE_QUESTION, reasons=["unattended"], attended=False, plan=True, plan_after=True
    ),
    "unattended_answers_a_draft": QuestionRow(
        CREATE_TASK, NO_ONE_DRAFT, reasons=["unattended"], attended=False
    ),
    "unattended_answers_an_edit_draft": QuestionRow(
        EDIT_TASK, NO_ONE_DRAFT, reasons=["unattended"], attended=False
    ),
    # -- exit_plan_mode
    "a_plan_outside_plan_mode_has_nothing_to_approve": QuestionRow(
        PLAN, "Plan mode isn't on", args={"plan": "step 1"}
    ),
    "approving_a_plan_switches_to_auto_mode": QuestionRow(
        PLAN,
        "switched to auto mode",
        plan=True,
        answer="auto",
        args={"plan": "step 1"},
        sent="plan_ready",
        auto_after=True,
    ),
    "approving_a_plan_by_hand_leaves_plan_mode": QuestionRow(
        PLAN,
        "will approve each change as you go",
        plan=True,
        answer="manual",
        args={"plan": "step 1"},
        sent="plan_ready",
    ),
    "feedback_keeps_plan_mode_on": QuestionRow(
        PLAN,
        "keep planning: add tests.",
        plan=True,
        answer="revise: add tests",
        args={"plan": "step 1"},
        sent="plan_ready",
        plan_after=True,
    ),
    "feedback_without_details": QuestionRow(
        PLAN,
        "keep planning: (no details).",
        plan=True,
        answer="revise:",
        args={"plan": "step 1"},
        sent="plan_ready",
        plan_after=True,
    ),
    "any_other_answer_to_a_plan_is_passed_on": QuestionRow(
        PLAN,
        "later",
        plan=True,
        answer="later",
        args={"plan": "step 1"},
        sent="plan_ready",
        plan_after=True,
    ),
    # -- create_scheduled_task and edit_scheduled_task
    "a_draft_is_answered": QuestionRow(
        CREATE_TASK,
        "Saved as Daily.",
        answer="Saved as Daily.",
        args={"name": "Daily"},
        sent="task_draft_required",
    ),
    "a_draft_is_not_blocked_by_plan_mode": QuestionRow(
        CREATE_TASK,
        "Dismissed.",
        plan=True,
        answer="Dismissed.",
        args={"name": "Daily"},
        sent="task_draft_required",
        plan_after=True,
    ),
    "an_edit_of_a_missing_task_is_answered_without_asking": QuestionRow(
        EDIT_TASK, "No scheduled task with id 'nope'", args={"trigger_id": "nope"}
    ),
}


@pytest.mark.parametrize("name", sorted(QUESTION_ROWS))
async def test_a_question_tool_answers_with_respond(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = QUESTION_ROWS[name]
    session = _session(tmp_path, monkeypatch)
    session._stop_requested = row.stop
    session.plan_mode = row.plan
    _write_exec_rule(session, row.exec_rule)
    _veto(monkeypatch, session, row.veto)
    socket = _Socket(row.attended)

    result = await _decide(session, row.tool, socket, answer=row.answer, args=row.args)

    assert result["type"] == "respond"
    assert row.message in result["message"]
    logged = AuditLog(session.settings.state_dir).read_all()
    assert [entry.reason for entry in logged] == row.reasons
    assert {entry.decision for entry in logged} <= {"reject"}
    sent = [m["type"] for m in socket.sent if m["type"] != "state"]
    assert sent == ([row.sent] if row.sent else [])
    assert session.plan_mode is row.plan_after
    assert session.auto_mode is row.auto_after
    assert not session._pending_questions


@pytest.mark.parametrize(("tool", "consulted"), [(EXEC, 1), (LOCAL, 0), (EXTERNAL, 0)])
async def test_the_exec_policy_is_read_for_scripts_only(
    tool: str, consulted: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    _write_exec_rule(session, "forbidden")
    reads: list[Path] = []
    real = session_module.load_exec_policy

    def spy(path: Path) -> Any:
        reads.append(path)
        return real(path)

    monkeypatch.setattr(session_module, "load_exec_policy", spy)

    result = await _decide(session, tool, _Socket(True), answer=True)

    assert len(reads) == consulted
    assert result["type"] == ("reject" if consulted else "approve")
