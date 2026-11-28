"""The approval decision: what runs without asking, what is refused, and what
waits for a person. It lives apart from ChatSessionLG so the security-relevant
precedence can be read, owned and tested on its own; the session keeps the
pending-approval futures and their resolution, the socket and the hooks.
"""

from __future__ import annotations

import json
import uuid
from asyncio import Future, get_running_loop, to_thread
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, Protocol

from ..code_runtime import CodePermissions
from ..config import Settings
from ..runtime_lg import (
    CODE_APPROVAL_RISKS,
    CODE_COMMAND_TOOL,
    EXEC_POLICY_TOOL_NAMES,
    AuditDecision,
    AuditLog,
    AuditReason,
    AutoApproveReason,
    ExecPolicy,
    Verdict,
    record_decision,
)
from ..tools import (
    PLAN_CHOICE_AUTO,
    PLAN_CHOICE_MANUAL,
    PLAN_CHOICE_REJECT,
    PLAN_CHOICE_REVISE,
    QUESTION_TOOL_NAMES,
    TASK_DRAFT_TOOL_NAMES,
    ScheduledTriggerStore,
    TaskToolkit,
    WorkspaceScope,
    edit_draft,
    expect_sandbox,
    format_question_answers,
    normalize_questions,
    parse_run_thread_id,
)
from .approval_scope import command_rule, review_call, reviewer_where, similar_call
from .capability_guard import capability_refusal, plugin_refusal
from .events import EventSink
from .folder_access import decide_folder_request
from .package_install import decide_package_install
from .wire import AskReason
from .workspace_folder import WorkspaceFolders
from .workspace_permissions import FolderVerdict, WorkspacePermissions

_COMMAND_TOOL = "run_background_command"
_MEMORY_HERE = "Save for this folder"
_MEMORY_SAVE = "Save everywhere"

# The line before the approved task list in exit_plan_mode's result; the frontend finds the list
# after it, live and in a replayed history (frontend/src/lib/planTasksResult.ts).
PLAN_TASKS_MARKER = "Task list as approved:"

_REPLIED_INSTEAD = (
    "The user didn't approve this call and wrote this instead; do what they ask rather than "
    "trying the same call again:\n{reply}"
)


def question_answer(data: dict[str, Any]) -> str | list[str | None] | dict[str, Any] | None:
    """The answer a tab's question_response carries: None when the questions were closed,
    `{"reply": text}` when the person wrote in the chat instead of choosing, one answer per
    question, a plain answer (a plan's or a task draft's), or `{"answer", "tasks"}` for a plan
    whose task list the person edited."""
    if data.get("dismissed"):
        return None
    if isinstance(data.get("answer"), str) and isinstance(data.get("tasks"), list):
        # Blank steps are dropped here, so Revise describes the list approving would keep.
        tasks = [
            {"content": content} | ({"id": str(t["id"])} if "id" in t else {})
            for t in data["tasks"]
            if isinstance(t, dict) and (content := str(t.get("content", "")).strip())
        ]
        return {"answer": data["answer"], "tasks": tasks}
    if isinstance(data.get("reply"), str):
        return {"reply": data["reply"]}
    answers = data.get("answers")
    if isinstance(answers, list):
        return [None if a is None else str(a) for a in answers]
    return str(data.get("answer", ""))


def _unattended_answer(name: str, is_draft: bool, *, plan_mode: bool) -> str:
    if is_draft:
        return (
            "No one is available to review this draft -- this is an unattended run, "
            "so no task was created."
        )
    if name == "exit_plan_mode" and not plan_mode:
        # The instructions ask for a review before a large task, and a scheduled run must
        # still do its work when no one can give one.
        return (
            "No one is available to review this plan -- this is an unattended run. "
            "Carry it out now."
        )
    return "No one is available to answer this question -- this is an unattended run."


def _memory_question(line: str, folder: Path) -> dict[str, Any]:
    question = (
        f'Save "{line}"? For this folder it is read whenever a conversation works in '
        f"{folder.name or folder}; your global instructions are read in every conversation."
    )
    options = [{"label": _MEMORY_HERE}, {"label": _MEMORY_SAVE}, {"label": "Don't save"}]
    return {"questions": [{"question": question, "header": "Remember", "options": options}]}


def _saved_to_memory(
    path: Path, notes: WorkspaceFolders, folder: Path, line: str, answer: dict[str, Any]
) -> dict[str, Any]:
    """The model only proposes the line: it is written here, and only on the person's Save."""
    choice = answer.get("message")
    if not line or choice not in (_MEMORY_HERE, _MEMORY_SAVE):
        return {"type": "respond", "message": "The user didn't save it. Don't offer it again."}
    if choice == _MEMORY_HERE:
        notes.add_note(folder, line)
        saved = f"Saved to the notes for {folder}. Don't offer it again."
        return {"type": "respond", "message": saved}
    current = path.read_text(encoding="utf-8").rstrip() if path.is_file() else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{current}\n- {line}\n".lstrip("\n"), encoding="utf-8")
    saved = "Saved to the user's global instructions. Don't offer it again."
    return {"type": "respond", "message": saved}


def can_resolve_approvals(websocket: Any) -> bool:
    """True for a real client connection able to actually answer an
    approval_required prompt; False for a silent/background stand-in
    (runtime_lg/selfwake.py's SilentSocket, driving an unattended
    sleep/wake or Scheduled Task turn) where nobody is present to ever
    resolve one. Checked via a duck-typed attribute, not isinstance, so
    the selfwake module needs no import of this one. A real fastapi
    WebSocket has no such attribute, so it defaults True, unchanged.

    Calling _resolve_pending_approvals anyway when this is False would
    create a real asyncio.Future and await it, resolved only by a genuine
    incoming WS message that a silent caller will never send -- verified
    live, this hangs the calling coroutine forever, which for a poll-loop
    caller (poll_due_wakes/poll_due_scheduled_tasks) wedges the *entire*
    background poller on the very first unattended run that happens to
    touch a gated tool. Skipping the call instead leaves the interrupt
    durably paused in the checkpointer, exactly what
    resume_after_reconnect already expects to find and resolve once a
    real client opens that thread."""
    return getattr(websocket, "can_resolve_approvals", True)


class SubAgentChannel:
    """What the decision tells a sub-agent's approval channel from a
    conversation's own socket by; the session's channel class extends it."""

    @property
    def delegated_task(self) -> str:
        raise NotImplementedError

    @property
    def task_id(self) -> str:
        raise NotImplementedError

    @property
    def can_resolve_approvals(self) -> bool:
        raise NotImplementedError


class ApprovalHost(Protocol):
    """What the decision reads and calls on the session it decides for."""

    thread_id: str
    settings: Settings
    workspace_root: Path
    config: dict[str, Any]
    model: Any
    lg_agent: Any
    plan_mode: bool
    accept_edits: bool
    auto_mode: bool
    bypass_mode: bool
    run_approval_mode: str | None
    preapproved_tools: frozenset[str]
    enabled_skill_names: set[str]
    _gated_tool_risks: dict[str, str]
    _stop_requested: bool
    _auto_paused: bool
    _auto_blocks_in_row: int
    _auto_blocks_total: int
    _pending_approvals: dict[str, Future[bool | str]]
    _pending_questions: dict[str, Future[Any]]
    _subagent_request_ids: set[str]
    _code_requests: dict[str, tuple[str, str]]
    _code_task_allowances: set[tuple[str, str]]
    _similar_allowances: set[str]
    _similar_requests: set[str]

    @property
    def folders(self) -> Sequence[Path]: ...

    @property
    def _reconfigurer(self) -> Any:  # SessionReconfigurer: rebuilds the tools after a folder card
        ...

    @property
    def _assembly(self) -> Any:  # AgentAssembly: its side_model() runs the reviewer
        ...

    def _toggle_mode(self, mode: str) -> None: ...

    async def send_state(self, websocket: EventSink, *, with_turn: bool = False) -> None: ...

    async def _send_tool_started(
        self, name: str, args: dict[str, Any], websocket: EventSink
    ) -> None: ...

    async def _run_pre_tool_use_hooks(self, name: str, args: dict[str, Any]) -> str | None: ...

    async def _build_document_edit_preview(
        self, tool_name_: str, args: dict[str, Any]
    ) -> tuple[str | None, str | None]: ...

    async def _auto_review(
        self, name: str, args: dict[str, Any], *, delegated_task: str = "", where: str = ""
    ) -> Verdict | None: ...

    def _load_exec_policy(self) -> ExecPolicy: ...

    def tool_catalog(self) -> dict[str, Any]: ...

    def workspace_scope(self) -> WorkspaceScope: ...


class ApprovalDecider:
    def __init__(self, host: ApprovalHost) -> None:
        self._host = host
        # What the turn is waiting on, by request id: a tab opened meanwhile
        # is shown it again (see ConversationHistory.send_history).
        self.open_prompts: dict[str, dict[str, Any]] = {}
        # (runtime, package) the person turned down on an install card in this conversation.
        self.declined_packages: set[tuple[str, str]] = set()

    async def _ask(self, websocket: Any, event: dict[str, Any]) -> None:
        # A sub-agent's approval waits on its task, which the panel shows.
        if not isinstance(websocket, SubAgentChannel):
            self.open_prompts[str(event["id"])] = event
        await websocket.send_json(event)

    async def _decide_action_request(
        self, request: dict[str, Any], websocket: Any, *, honor_stop: bool = True
    ) -> Any:
        """Decide one pending action request. A configured PreToolUse hook can veto it outright
        (it runs before the approval policy it would otherwise reach); a tool in
        self._gated_tool_risks then goes through `_decide_gated_request`, which holds the
        precedence. Any other tool reached here only because PreToolUse hooks are configured
        (__init__'s extra_interrupt_tool_names) and passed them, so it's approved, plan mode or
        not: it never needed approval.

        A name in QUESTION_TOOL_NAMES is answered, never approved: its interrupt allows only a
        "respond" decision (runtime_lg/agent.py's `question_tool_names`), so each early exit below
        denies it through `_denied`, whose message the model reads as the tool's result. A card
        that changes something (a folder, a package) audits the person's answer itself.

        A stop already requested refuses before any card: request_stop denies the futures
        already waiting, and this covers a request decided after it (the next task of
        _resolve_pending_approvals's loop). Every other branch that decides a gated call,
        attended or not, leaves an audit record (runtime_lg/audit.py), a hook veto too."""
        name = request["name"]
        is_draft = name in TASK_DRAFT_TOOL_NAMES
        is_question = name in QUESTION_TOOL_NAMES or is_draft
        if honor_stop and self._host._stop_requested:
            return self._denied(name, "Stopped by user.")
        args = request["args"]
        audit_log = AuditLog(self._host.settings.state_dir)
        hook_reason = await self._host._run_pre_tool_use_hooks(name, args)
        if hook_reason is not None:
            self._audit(audit_log, name, args, "reject", "hook_veto", hook_reason)
            return self._denied(name, hook_reason)
        if is_question:
            if not can_resolve_approvals(websocket):
                message = _unattended_answer(name, is_draft, plan_mode=self._host.plan_mode)
                self._audit(audit_log, name, args, "reject", "unattended", message)
                return self._denied(name, message)
            if is_draft:
                return await self._decide_task_draft_request(name, args, websocket)
            if name == "exit_plan_mode":
                return await self._decide_plan_request(args, websocket)
            if name == "request_folder_access":
                return await decide_folder_request(
                    self._host, args, websocket, self._ask, self.open_prompts
                )
            if name == "install_package":
                return await decide_package_install(self, args, websocket)
            if name == "remember":
                line = str(args.get("line", "")).strip()
                folder = Path(self._host.workspace_root)
                question = _memory_question(line, folder)
                answer = await self._decide_question_request(question, websocket)
                memory = Path(self._host.settings.memory_path)
                notes = self._host._assembly.workspace_folders
                return _saved_to_memory(memory, notes, folder, line, answer)
            return await self._decide_question_request(args, websocket)
        if name not in self._host._gated_tool_risks:
            return {"type": "approve"}
        return await self._decide_gated_request(name, args, websocket, audit_log)

    def _denied(self, name: str, message: str) -> dict[str, Any]:
        if name in QUESTION_TOOL_NAMES or name in TASK_DRAFT_TOOL_NAMES:
            return {"type": "respond", "message": message}
        return {"type": "reject", "message": message}

    def _audit(
        self,
        audit_log: AuditLog,
        name: str,
        args: dict[str, Any],
        decision: AuditDecision,
        reason: AuditReason,
        detail: str | None = None,
        asked_because: AskReason | None = None,
    ) -> None:
        record_decision(
            audit_log,
            thread_id=self._host.thread_id,
            tool_name=name,
            arguments=args,
            decision=decision,
            reason=reason,
            detail=detail,
            asked_because=asked_because,
        )

    async def _approved(
        self,
        audit_log: AuditLog,
        name: str,
        args: dict[str, Any],
        websocket: Any,
        reason: AuditReason | AutoApproveReason,
        detail: str | None = None,
    ) -> dict[str, Any]:
        self._audit(audit_log, name, args, "approve", reason, detail)
        state_dir, thread = self._host.settings.state_dir, self._host.thread_id
        if name == _COMMAND_TOOL and command_rule(state_dir, thread) is None:
            # Approved on the ground that the sandbox holds it; counted only here, so a rejected
            # command leaves nothing for a later one to inherit (one approved without it, 0062).
            expect_sandbox(thread)
        await self._host._send_tool_started(name, args, websocket)
        return {"type": "approve"}

    async def _decide_gated_request(
        self, name: str, args: dict[str, Any], websocket: Any, audit_log: AuditLog
    ) -> Any:
        """The precedence for a gated tool once no hook has vetoed it: exec policy forbids, the
        workspace denies, its switch is off, plan mode, the workspace asks, Bypass mode, an
        "allow similar", a command the person approves outside Auto mode (0022), exec policy or
        the workspace allows, then `_decide_by_mode`."""
        exec_policy_decision, exec_policy_detail = "prompt", None
        if name in EXEC_POLICY_TOOL_NAMES:
            exec_policy = self._host._load_exec_policy()
            exec_policy_decision, exec_policy_detail = exec_policy.decide(args.get("script", ""))
        if exec_policy_decision == "forbidden":
            message = exec_policy_detail or "Forbidden by exec policy."
            self._audit(audit_log, name, args, "reject", "exec_policy", message)
            return {"type": "reject", "message": message}
        folder_rule = self._folder_rule(name, args)
        if folder_rule is not None and folder_rule[0] == "deny":
            message = f"The workspace's settings deny this ({folder_rule[1]})."
            self._audit(audit_log, name, args, "reject", "workspace_settings", message)
            return {"type": "reject", "message": message}
        turned_off = self._turned_off(name, args)
        if turned_off is not None:
            self._audit(audit_log, name, args, "reject", "capability_off", turned_off)
            return {"type": "reject", "message": turned_off}
        if self._host.plan_mode:
            message = (
                "Plan mode is active (read-only). Note this step with "
                "task_create instead; the user needs to turn plan mode "
                "off before it can run."
            )
            self._audit(audit_log, name, args, "reject", "plan_mode", message)
            return {"type": "reject", "message": message}
        if folder_rule is not None and folder_rule[0] == "ask":
            note = f"The workspace's settings ask for this ({folder_rule[1]})."
            return await self._ask_person_only(
                audit_log, name, args, websocket, "workspace_rule", note
            )
        if (bypass := self._bypass()) is not None:
            return await self._approved(audit_log, name, args, websocket, bypass)
        similar = similar_call(name, args)
        if similar is not None and similar.key in self._host._similar_allowances:
            return await self._approved(audit_log, name, args, websocket, "allowed_similar")
        # A code task's commands, approved once for the task, run in the same sandbox (#616).
        rule = None
        if name in (_COMMAND_TOOL, CODE_COMMAND_TOOL):
            rule = command_rule(self._host.settings.state_dir, self._host.thread_id)
            if rule is not None and not self._auto_review_active():
                return await self._ask_person_only(audit_log, name, args, websocket, rule)
        if rule is not None:  # allow rules count on the sandbox: the reviewer decides this one
            return await self._decide_by_mode(audit_log, name, args, websocket, rule)
        if exec_policy_decision == "allow":
            return await self._approved(
                audit_log, name, args, websocket, "exec_policy", exec_policy_detail
            )
        if folder_rule is not None:
            return await self._approved(
                audit_log, name, args, websocket, "workspace_settings", folder_rule[1]
            )
        return await self._decide_by_mode(audit_log, name, args, websocket, rule)

    async def _decide_by_mode(
        self,
        audit_log: AuditLog,
        name: str,
        args: dict[str, Any],
        websocket: Any,
        rule: AskReason | None,
    ) -> Any:
        """A call no rule decided: an allowance, the mode, Auto mode's reviewer, or a person."""
        if self._code_allows(name, websocket):
            return await self._approved(audit_log, name, args, websocket, "code_allowed")
        # A command 0022 keeps from the person's own approvals goes to Auto mode's reviewer.
        auto_reason = None if rule is not None else self._auto_approves(name)
        if auto_reason is not None:
            return await self._approved(audit_log, name, args, websocket, auto_reason)
        reviewer_note: str | None = None
        because: AskReason = rule or "approval_mode"
        if self._auto_review_active():
            decision, reviewer_note = await self._auto_review_decision(
                audit_log, name, args, websocket, reviewer_where(rule)
            )
            if decision is not None:
                return decision
            # Only a run of blocks pauses Auto mode; a reviewer with no answer leaves it on.
            because = "auto_review_blocked" if self._host._auto_paused else "auto_review_no_answer"
        return await self._ask_person_only(audit_log, name, args, websocket, because, reviewer_note)

    def _folder_rule(self, name: str, args: dict[str, Any]) -> tuple[FolderVerdict, str] | None:
        root = Path(self._host.workspace_root)
        settings = self._host._assembly.workspace_folders.accepted_settings(root)
        if not settings:
            return None
        metadata = self._host.tool_catalog().get(name)
        risk = getattr(metadata, "risk_category", None)
        return WorkspacePermissions(settings, root).decide(name, args, risk)

    def _turned_off(self, name: str, args: dict[str, Any]) -> str | None:
        """Asked before a person is: nobody approves a write its switch then refuses."""
        held = plugin_refusal(name, self._host.enabled_skill_names)
        if held is not None:
            return held
        metadata = self._host.tool_catalog().get(name)
        if metadata is None:
            return None
        state_dir = self._host.settings.state_dir
        return capability_refusal(state_dir, name, metadata, args, self._host.workspace_scope)

    async def _ask_person_only(
        self,
        audit_log: AuditLog,
        name: str,
        args: dict[str, Any],
        websocket: Any,
        because: AskReason,
        reviewer_note: str | None = None,
    ) -> Any:
        if not can_resolve_approvals(websocket):
            # A normal unattended turn never gets here (its interrupt stays paused in the
            # checkpointer); an unattended run with accept_edits or auto mode on does, and a
            # Future would wait on a person nobody is present to be.
            message = "No one is available to approve this -- this is an unattended run."
            self._audit(audit_log, name, args, "reject", "unattended", message, because)
            return self._denied(name, message)
        return await self._ask_person(audit_log, name, args, websocket, because, reviewer_note)

    async def _auto_review_decision(
        self, audit_log: AuditLog, name: str, args: dict[str, Any], websocket: Any, where: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        """The auto reviewer's verdict: a decision to return now, or None
        to fall through to a person, with the note that explains why."""
        task = getattr(websocket, "delegated_task", "")
        verdict = await self._host._auto_review(name, args, delegated_task=task, where=where)
        if verdict is None:
            return None, "Auto mode's reviewer gave no answer for this, so it's asking you."
        if verdict.allow:
            self._host._auto_blocks_in_row = 0
            return (
                await self._approved(
                    audit_log, name, args, websocket, "auto_review", verdict.reason
                ),
                None,
            )
        self._host._auto_blocks_in_row += 1
        self._host._auto_blocks_total += 1
        self._audit(audit_log, name, args, "reject", "auto_review_block", verdict.reason)
        if self._host._auto_blocks_in_row < 3 and self._host._auto_blocks_total < 20:
            return (
                self._denied(
                    name,
                    f"Auto mode blocked this: {verdict.reason} Find another way, or ask "
                    "the user to allow this specific action.",
                ),
                None,
            )
        self._host._auto_paused = True
        if self._host._auto_blocks_total >= 20:
            self._host._auto_blocks_total = 0
        return None, f"Auto mode kept blocking actions, so it's asking you: {verdict.reason}"

    async def _ask_person(
        self,
        audit_log: AuditLog,
        name: str,
        args: dict[str, Any],
        websocket: Any,
        because: AskReason,
        reviewer_note: str | None,
    ) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        # True or False from the card, or the words the person wrote in the chat instead.
        future: Future[bool | str] = get_running_loop().create_future()
        self._host._pending_approvals[request_id] = future
        if isinstance(websocket, SubAgentChannel):
            self._host._subagent_request_ids.add(request_id)
            if name in CODE_APPROVAL_RISKS:
                self._host._code_requests[request_id] = (websocket.task_id, name)
        # The preview costs an office-program conversion and a dry-run edit: only worth it for
        # a card someone can see.
        before_preview, after_preview = (
            await self._host._build_document_edit_preview(name, args)
            if can_resolve_approvals(websocket)
            else (None, None)
        )
        await self._ask(
            websocket,
            {
                "type": "approval_required",
                "id": request_id,
                "tool_name": name,
                "arguments": args,
                "before_preview": before_preview,
                "after_preview": after_preview,
                "reviewer_note": reviewer_note,
                "asked_because": because,
                "allow_similar": similar.allow_similar
                if (similar := similar_call(name, args))
                else None,
            },
        )
        try:
            decision = await future
        finally:
            self._host._pending_approvals.pop(request_id, None)
            self.open_prompts.pop(request_id, None)
            self._host._subagent_request_ids.discard(request_id)
            self._host._code_requests.pop(request_id, None)
        if isinstance(decision, str):
            self._audit(audit_log, name, args, "reject", "human", decision, because)
            return {"type": "reject", "message": _REPLIED_INSTEAD.format(reply=decision)}
        approved = decision
        if request_id in self._host._similar_requests:
            self._host._similar_requests.discard(request_id)
            if approved and (similar := similar_call(name, args)) is not None:
                self._host._similar_allowances.add(similar.key)
        if approved and self._host._auto_paused:
            self._host._auto_paused = False
            self._host._auto_blocks_in_row = 0
        decided: AuditDecision = "approve" if approved else "reject"
        self._audit(audit_log, name, args, decided, "human", asked_because=because)
        return {"type": decided}

    async def _decide_question_request(
        self, args: dict[str, Any], websocket: EventSink
    ) -> dict[str, Any]:
        """The ask_user_question flow: send question_required, wait for a
        real person's answer, and return it as a "respond" decision --
        HumanInTheLoopMiddleware substitutes this message directly as the
        tool's own result, the tool's Python body never actually running
        (see tools/bookkeeping/interaction.py's own docstring). Same pending-Future/
        request-id shape as the approval flow just above, kept as a
        separate dict (self._pending_questions) rather than reusing
        self._pending_approvals since the value type is different (a
        free-text answer, not a bool) and request_stop/reconnect need to
        treat the two independently."""
        request_id = uuid.uuid4().hex
        future: Future[Any] = get_running_loop().create_future()
        self._host._pending_questions[request_id] = future
        questions = normalize_questions(args)
        await self._ask(
            websocket, {"type": "question_required", "id": request_id, "questions": questions}
        )
        try:
            reply = await future
        finally:
            self._host._pending_questions.pop(request_id, None)
            self.open_prompts.pop(request_id, None)
        return {"type": "respond", "message": format_question_answers(questions, reply)}

    async def _decide_plan_request(
        self, args: dict[str, Any], websocket: EventSink
    ) -> dict[str, Any]:
        """exit_plan_mode: the user approves the plan -- in auto mode, or approving changes
        as before (leaving plan mode for Manual when it was on) -- or keeps planning with
        feedback. Outside plan mode the model asks for this review itself before a large task.
        The task list the person edited meanwhile becomes the plan's list when they approve."""
        request_id = uuid.uuid4().hex
        future: Future[Any] = get_running_loop().create_future()
        self._host._pending_questions[request_id] = future
        await self._ask(
            websocket, {"type": "plan_ready", "id": request_id, "plan": str(args.get("plan", ""))}
        )
        try:
            answer = await future
        finally:
            self._host._pending_questions.pop(request_id, None)
            self.open_prompts.pop(request_id, None)
        if answer is None:
            return {
                "type": "respond",
                "message": "The user closed the plan without answering. Don't carry it out; "
                "wait for their next message.",
            }
        if isinstance(answer, dict) and isinstance(answer.get("reply"), str):
            return {"type": "respond", "message": _REPLIED_INSTEAD.format(reply=answer["reply"])}
        edits: list[dict[str, Any]] | None = None
        if isinstance(answer, dict) and "answer" in answer:
            edits, answer = answer.get("tasks"), answer["answer"]
        if not isinstance(answer, str):
            answer = str(answer)
        if answer in (PLAN_CHOICE_AUTO, PLAN_CHOICE_MANUAL):
            host = self._host
            if answer == PLAN_CHOICE_AUTO:
                how = "kept auto mode on" if host.auto_mode else "switched to auto mode"
                if not host.auto_mode:
                    host._toggle_mode("auto")
                # The reviewer may have paused itself; this answer asks for it again.
                host._auto_paused = False
                host._auto_blocks_in_row = 0
            else:
                for mode, on in (
                    ("plan", host.plan_mode),
                    ("auto", host.auto_mode),
                    ("accept-edits", host.accept_edits),
                ):
                    if on:
                        host._toggle_mode(mode)
                how = "will approve each change as you go"
            await host.send_state(websocket)
            message = f"The user approved the plan and {how}. Carry it out now."
            if edits is not None:
                toolkit = TaskToolkit(host.thread_id, host.settings.state_dir)
                approved = await to_thread(toolkit.replace, edits)
                message += (
                    " They edited your task list: carry out this one, in this order, and "
                    "task_update these ids; a step they removed is not to be done.\n"
                    f"{PLAN_TASKS_MARKER}\n{json.dumps(approved, ensure_ascii=False)}"
                )
            return {"type": "respond", "message": message}
        if answer == PLAN_CHOICE_REJECT:
            return {
                "type": "respond",
                "message": "The user rejected the plan. Don't carry it out and don't propose "
                "another one; stop and wait for their next message.",
            }
        if isinstance(answer, str) and answer.startswith(PLAN_CHOICE_REVISE):
            feedback = answer[len(PLAN_CHOICE_REVISE) :].strip() or "(no details)"
            if edits is not None:
                steps = "\n".join(f"{i}. {t['content']}" for i, t in enumerate(edits, 1))
                feedback += f"\n\nThe task list as they left it:\n{steps}"
            return {
                "type": "respond",
                "message": f"The user wants to keep planning: {feedback}. Revise the plan "
                "and call exit_plan_mode again.",
            }
        return {"type": "respond", "message": answer}

    async def _decide_task_draft_request(
        self, name: str, args: dict[str, Any], websocket: EventSink
    ) -> dict[str, Any]:
        """create_scheduled_task's review flow: the frontend shows the
        draft, the user edits and saves it (through the ordinary REST
        create endpoint, with its full validation) or dismisses it, and
        answers with a sentence saying which -- substituted as the tool's
        result. Shares the pending-question plumbing, since the answer is
        likewise a string and stop/reconnect treat it the same way."""
        draft = args
        if name == "edit_scheduled_task":
            # The whole task as it would be saved, so the review shows it
            # in the edit form rather than as a partial list of fields.
            try:
                draft = edit_draft(ScheduledTriggerStore(self._host.settings.state_dir), args)
            except KeyError as exc:
                message = f"{exc.args[0]} -- check list_scheduled_tasks."
                return {"type": "respond", "message": message}
        request_id = uuid.uuid4().hex
        future: Future[str] = get_running_loop().create_future()
        self._host._pending_questions[request_id] = future
        await self._ask(
            websocket, {"type": "task_draft_required", "id": request_id, "draft": draft}
        )
        try:
            answer = await future
        finally:
            self._host._pending_questions.pop(request_id, None)
            self.open_prompts.pop(request_id, None)
        return {"type": "respond", "message": answer}

    def _auto_approves(self, name: str) -> AutoApproveReason | None:
        """Why a gated call may go ahead without asking anyone, or None. A run's "skip" approves
        every risk tier, its "auto" only WRITE_LOCAL: a local edit can be redone, running code or
        acting outside this machine can't. Auto mode lets a file or document edit through without
        its reviewer, as Accept Edits does: the tools keep it inside the conversation's folders."""
        if name in self._host.preapproved_tools:
            return "preapproved"
        local = self._host._gated_tool_risks.get(name) == "WRITE_LOCAL"
        if self._host.accept_edits and local:
            return "accept_edits"
        mode = self._effective_run_approval_mode()
        if mode == "skip":
            return "approval_mode_skip"
        if mode == "auto" and local:
            return "approval_mode_auto"
        category = getattr(self._host.tool_catalog().get(name), "category", None)
        # A delete or a move takes away a file that was there before: the reviewer sees those.
        edits = category in ("filesystem", "documents") and name not in ("delete_file", "move_file")
        if self._auto_review_active() and local and edits:
            return "auto_mode_edit"
        return None

    def _effective_run_approval_mode(self) -> str | None:
        """The scheduled-run approval tier in force here: the executing
        run's, or -- while a person finishes a run that parked on an
        approval -- that run's task's, so the rest of the run keeps the
        rules it started under. None for an ordinary conversation."""
        if self._host.run_approval_mode is not None:
            return self._host.run_approval_mode
        parsed = parse_run_thread_id(self._host.thread_id)
        if parsed is None:
            return None
        trigger = ScheduledTriggerStore(self._host.settings.state_dir).load(parsed[0])
        if trigger is None:
            return None
        run = trigger.find_run(parsed[1])
        if run is None or run.status != "needs_approval":
            return None
        return trigger.tier(trigger.approval_mode, self._host.settings.allow_bypass_mode)

    def _code_allows(self, name: str, websocket: Any) -> bool:
        """Whether the user has allowed this kind of code-module action: on
        an earlier card for this task, or in Settings > Code for good."""
        if name not in CODE_APPROVAL_RISKS or not isinstance(websocket, SubAgentChannel):
            return False
        if (websocket.task_id, name) in self._host._code_task_allowances:
            return True
        # A switch set for the user at the keyboard doesn't reach a scheduled
        # run, whose task chose its own approval tier, or a turn nobody is
        # watching.
        if self._effective_run_approval_mode() is not None or not websocket.can_resolve_approvals:
            return False
        permissions = CodePermissions(self._host.settings.state_dir, tuple(CODE_APPROVAL_RISKS))
        return permissions.policy(name) == "allow"

    def _auto_review_active(self) -> bool:
        """The reviewer decides in the conversation's Auto mode, or in a run whose task approves
        "auto": the run's prompt is the person's request in its thread (decision 0062). A run
        keeps its task's tier, whatever the conversation's mode."""
        if self._host._auto_paused:
            return False
        mode = self._effective_run_approval_mode()
        return self._host.auto_mode if mode is None else mode == "auto"

    async def _auto_review(
        self, name: str, args: dict[str, Any], *, delegated_task: str = "", where: str = ""
    ) -> Verdict | None:
        return await review_call(self._host, name, args, delegated_task, where)

    def _bypass(self) -> Literal["bypass", "approval_mode_skip"] | None:
        """Bypass mode holds only while Settings allows it. A run keeps its task's tier, and a
        task's "skip" is Bypass's equal: `ScheduledTrigger.tier` holds it to the same setting."""
        mode = self._effective_run_approval_mode()
        if mode is not None:
            return "approval_mode_skip" if mode == "skip" else None
        on = self._host.bypass_mode and self._host.settings.allow_bypass_mode
        return "bypass" if on else None

    def _auto_approval_active(self) -> bool:
        return (
            self._host.accept_edits
            or bool(self._host.preapproved_tools)
            or self._auto_review_active()
            or self._bypass() is not None
            or self._effective_run_approval_mode() == "auto"
        )
