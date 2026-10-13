"""What a conversation decides about one gated tool call, as a table.

`ChatSessionLG._decide_action_request` decides what runs without asking, so before it is
split (the scale assessment, section 4) every combination that changes its answer is
written down here: the precedence of a stop, a hook veto, an exec-policy rule, plan mode,
the standing approvals (pre-approved, Accept Edits, a scheduled run's tier) and, last, asking
a person or refusing because nobody is there. Each row is run through the real method with a
fake socket; the decision, the audit record and whether the call was announced are all
checked. A row changes only when the decision it names is changed on purpose.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langgraph.checkpoint.memory import InMemorySaver

from coscribe.config import Settings
from coscribe.conversation import session as session_module
from coscribe.conversation.session import ChatSessionLG
from coscribe.runtime import empty_hooks_config
from coscribe.runtime_lg.audit import AuditLog

READ, LOCAL, EXEC, EXTERNAL = "read_file", "write_file", "run_python_script", "send_email"
RISKS = {LOCAL: "WRITE_LOCAL", EXEC: "EXEC", EXTERNAL: "EXTERNAL"}


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
    note: str = field(default="", compare=False)


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


async def _decide(session: ChatSessionLG, row: Row, socket: _Socket) -> dict[str, Any]:
    """Run the decision and answer any question it asks (a refusal when the row has no
    answer, so a decision that asks by mistake fails the assertions instead of hanging)."""
    request = {"name": row.tool, "args": {"script": "print(1)", "path": "a.txt"}}

    async def run() -> dict[str, Any]:
        task = asyncio.create_task(session._decide_action_request(request, socket))
        while not task.done():
            for future in session._pending_approvals.values():
                if not future.done():
                    future.set_result(bool(row.human))
            await asyncio.sleep(0)
        return task.result()  # type: ignore[no-any-return]

    return await asyncio.wait_for(run(), timeout=10)


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
    if row.exec_rule is not None:
        rules = [{"pattern": ".", "decision": row.exec_rule, "justification": "by the policy"}]
        session.settings.exec_policy_path.write_text(  # type: ignore[union-attr]
            json.dumps({"rules": rules}), encoding="utf-8"
        )

    async def veto(tool: str, args: dict[str, Any]) -> str | None:
        return row.veto

    monkeypatch.setattr(session, "_run_pre_tool_use_hooks", veto)
    socket = _Socket(row.attended)

    result = await _decide(session, row, socket)

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
