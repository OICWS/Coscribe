"""run_code_task: the conversation hands a programming task to the code
module (Codex, see code_runtime/) and gets back its report.

A run is a sub-agent like spawn_agent's -- the same task record, panel,
stop and approval path -- driven by Codex instead of a LangGraph child.
Codex's approval requests arrive as calls to two tools that exist only for
this, a command (EXEC) and a file change (WRITE_LOCAL), and are decided by
the host like any gated call: hooks, plan mode, the permission modes, a
scheduled task's approval tier and the audit log all apply. Its text and
tokens stay on its own record; nothing reaches the parent's chat stream.
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..code_runtime import (
    ApprovalRequest,
    CodeService,
    CodexEvent,
    CodexThread,
    CodexUnavailable,
    codex_model,
    shell_script,
)
from ..runtime import NetworkGuard, redactor, tool_metadata
from ..tools import (
    SubAgentTask,
    SubAgentTaskStore,
    code_command_profile,
    code_commands_allowed,
    register_subagent_run,
    take_stop_requester,
)
from .subagents import SubAgentHost, subagent_outcome

logger = logging.getLogger(__name__)

CODE_TASK_TOOL = "run_code_task"
CODE_COMMAND_TOOL = "run_code_command"
CODE_CHANGE_TOOL = "apply_code_change"
CODE_APPROVAL_RISKS = {CODE_COMMAND_TOOL: "EXEC", CODE_CHANGE_TOOL: "WRITE_LOCAL"}

_OUTPUT_CHARS = 4000

INSTRUCTIONS = """\
You are Coscribe's code module, doing one task handed over by Coscribe's \
office assistant, for a user who doesn't write code. Work in the current \
folder. Nobody can answer questions while you work: make reasonable \
assumptions and say what they were. {commands} Every figure or finding \
about the user's data must come from what a command printed, never typed in \
by hand. When done, reply with a short report in the language of the task: \
what you did, the files you created or changed, and anything left undone."""

COMMANDS_OFF = """\
Commands are turned off in coscribe: the only ones that run are plain \
listing or reading commands of this folder, one at a time (Get-ChildItem, \
Get-Content, Select-String; or ls, cat, head, grep) with no pipes or \
chaining. Anything else, python included, is refused, so you cannot run \
code, tests or builds, nor read an xlsx, docx or pdf; change files with your \
patch tool (each change may need the user's approval) and report what you \
couldn't do."""

SANDBOX_REQUEST = (
    "Any command and file change the code module makes for this task, in the command sandbox: "
    "it writes only {folder}, with this environment's network."
)

COMMANDS_SANDBOXED = """\
Your commands and file changes run in a sandbox without asking anyone: they \
can write only this folder, and may be offline. A request to run outside the \
sandbox is always refused, so don't make one; work within it, or report what \
you couldn't do. Run the code and tests you write to check them."""


@dataclass
class CodeTaskContext:
    """What the conversation lends a code run: the service, and its current
    model, folder and that model's context window."""

    service: Callable[[], CodeService]
    model: Callable[[], str]
    folder: Callable[[], Path]
    context_window: Callable[[], int | None]
    # The plain variables the user set for this conversation.
    env: Callable[[], dict[str, str]] = field(default=dict)


def command_args(command: str, description: str = "") -> dict[str, Any]:
    # The shape run_python_script's approval card and transcript row show.
    return {"script": shell_script(command) or command, "description": description}


def approval_call(request: ApprovalRequest) -> dict[str, Any]:
    """Codex's approval request as the gated call the host decides."""
    if request.kind == "command":
        return {"name": CODE_COMMAND_TOOL, "args": command_args(request.command, request.reason)}
    return {
        "name": CODE_CHANGE_TOOL,
        "args": {"paths": list(request.paths), "description": request.reason},
    }


class _Run:
    def __init__(
        self,
        host: SubAgentHost,
        store: SubAgentTaskStore,
        record: SubAgentTask,
        context: CodeTaskContext,
        previous: SubAgentTask | None = None,
    ) -> None:
        self.host = host
        self.store = store
        self.record = record
        self.context = context
        self.previous = previous
        # Codex is never given a secret, but what it prints is the model's
        # to read, so it goes through the same blanking as any tool result.
        self.redact = redactor(host.state_dir)
        self.entries: list[dict[str, Any]] = [{"kind": "user", "text": record.prompt}]

    async def save(self) -> None:
        self.store.save(self.record)
        await self.host.changed(self.record)

    async def decide(self, request: ApprovalRequest) -> bool:
        decision = await self.host.decide(approval_call(request), self.record)
        if self.record.pending_approval is not None or self.record.status != "running":
            self.record.pending_approval = None
            self.record.status = "running"
            await self.save()
        return isinstance(decision, dict) and decision.get("type") == "approve"

    async def on_event(self, event: CodexEvent) -> None:
        data = event.data
        if event.kind == "message" and data.get("text"):
            self.entries.append({"kind": "agent", "text": self.redact(data["text"])})
        elif event.kind == "command_started":
            self.record.tool_uses += 1
            self.record.last_tool = {
                "tool_name": CODE_COMMAND_TOOL,
                "arguments": command_args(str(data.get("command", ""))),
            }
            await self.save()
        elif event.kind == "command_finished":
            exit_code = data.get("exit_code")
            self.entries.append(
                {
                    "kind": "tool",
                    "tool_name": CODE_COMMAND_TOOL,
                    "arguments": command_args(str(data.get("command", ""))),
                    "result": {
                        "exit_code": exit_code,
                        "output": self.redact(str(data.get("output") or "")[-_OUTPUT_CHARS:]),
                    },
                    "is_error": data.get("status") != "completed" or exit_code not in (0, None),
                }
            )
        elif event.kind == "file_change":
            self.entries.append(
                {
                    "kind": "tool",
                    "tool_name": CODE_CHANGE_TOOL,
                    "arguments": {"paths": data.get("paths", [])},
                    "result": {"status": data.get("status")},
                    "is_error": data.get("status") != "completed",
                }
            )
        elif event.kind == "usage":
            self.record.tokens += int(data.get("totalTokens") or 0)
            await self.save()

    async def opened(self, thread_id: str) -> None:
        self.record.codex_thread = thread_id
        await self.save()

    async def sandbox(
        self, folder: Path, programs: list[Path]
    ) -> tuple[str, dict[str, str]] | None:
        """The profile Codex's commands run in, or None when they stay off (issue #616). Codex
        asks nothing in the sandbox, so its commands are approved once, here, as a
        conversation's command is: by the person whenever the environment is online."""
        state, thread_id = self.host.state_dir, self.record.thread_id
        if not await asyncio.to_thread(code_commands_allowed, state, thread_id):
            return None
        online = NetworkGuard(state, thread_id).scripts_online()
        request = ApprovalRequest(
            kind="command",
            item_id="sandbox",
            command=SANDBOX_REQUEST.format(folder=folder),
            reason=f"Code task: {self.record.description}",
        )
        if not await self.decide(request):
            return None
        sandbox = await asyncio.to_thread(code_command_profile, state, thread_id, folder, programs)
        # The approval was for the network as it was when asked; changed since, it doesn't hold.
        if NetworkGuard(state, thread_id).scripts_online() != online:
            return None
        return sandbox

    async def drive(self) -> None:
        record = self.record
        try:
            service = self.context.service()
            model = codex_model(self.context.model(), service.custom_providers())
            codex = await service.prepare()
            folder = self.context.folder()
            sandbox = await self.sandbox(folder, service.command_path())
            permissions, sandbox_env = sandbox if sandbox is not None else (None, {})
            commands = COMMANDS_SANDBOXED if permissions else COMMANDS_OFF
            previous = self.previous
            thread = CodexThread(
                codex,
                model,
                folder,
                thread_id=previous.codex_thread or None if previous else None,
                developer_instructions=INSTRUCTIONS.format(commands=commands),
                context_window=await asyncio.to_thread(self.context.context_window),
                fallback_context=_earlier_work(previous) if previous else "",
                env={**self.context.env(), **sandbox_env},
                on_open=self.opened,
                permissions=permissions,
            )
            result = await thread.run_turn(record.prompt, self.decide, self.on_event)
        except asyncio.CancelledError:
            record.status = "stopped"
            record.stopped_by = take_stop_requester(record.task_id)
            record.pending_approval = None
            record.finished_at = datetime.now(UTC).isoformat()
            await self.save()
            raise
        except Exception as exc:  # noqa: BLE001 -- a failed run is reported, not raised into the parent
            logger.warning("code run %s failed", record.task_id, exc_info=True)
            record.status = "failed"
            record.error = (str(exc) or type(exc).__name__)[:2000]
            record.finished_at = datetime.now(UTC).isoformat()
            await self.save()
            return
        if result.status == "completed":
            report = result.text or "(the code module gave no reply)"
            if result.files_changed:
                report += f"\n\nFiles created or changed in {folder}: " + ", ".join(
                    result.files_changed
                )
            record.result = self.redact(report)
            record.status = "succeeded"
        else:
            record.status = "failed"
            record.error = result.error or f"the run ended {result.status}"
        record.finished_at = datetime.now(UTC).isoformat()
        await self.save()


def _earlier_work(previous: SubAgentTask) -> str:
    """What a follow-up is told when Codex no longer has the thread it carries
    on: the earlier task and what came of it."""
    outcome = previous.result or previous.error or "(no report)"
    return (
        "You are carrying on from an earlier task of this folder, whose history is no "
        f"longer available.\nThe earlier task:\n{previous.prompt}\nIts report:\n{outcome}\n"
        "What the user wants now:"
    )


_TASK_ID = re.compile(r"[0-9a-f]{12}")


def _continuation(
    store: SubAgentTaskStore, task_id: str, thread_id: str
) -> tuple[SubAgentTask | None, str]:
    """The task to carry on from, or why there isn't one. Everything here is
    synchronous and the new record is saved before the caller first awaits, so
    two follow-ups chosen in one message can't both pass."""
    # The id is the model's, and names a file: only what this tool made.
    previous = store.load(task_id) if _TASK_ID.fullmatch(task_id) else None
    if (
        previous is None
        or previous.thread_id != thread_id
        or not previous.model.startswith("codex:")
    ):
        return None, (
            "continue_task isn't a code task of this conversation (it may have been cleared "
            "from the Sub Agents panel). Start a new task instead."
        )
    if not previous.codex_thread:
        return None, (
            "That code task never got as far as starting, so there is nothing to carry on. "
            "Start a new task with the full instructions."
        )
    # Two turns can't run in one Codex thread at once, whichever task of it
    # is the one named.
    if any(
        sibling.codex_thread == previous.codex_thread
        and sibling.status in ("running", "needs_approval")
        for sibling in store.list_for_thread(thread_id)
    ):
        return None, "That code task is still running; wait for its report before continuing it."
    return previous, ""


def _report(record: SubAgentTask) -> str:
    """The run's outcome for the conversation, with the id a follow-up needs."""
    outcome = subagent_outcome(record)
    if not record.codex_thread:
        return outcome
    return (
        f"{outcome}\n\n(Code task {record.task_id}: to change or fix its work, call "
        f'run_code_task again with continue_task="{record.task_id}".)'
    )


def build_code_task_tool(host: SubAgentHost, context: CodeTaskContext) -> Callable[..., Any]:
    store = SubAgentTaskStore(host.state_dir)

    async def run_code_task(description: str, task: str, continue_task: str = "") -> str:
        """Hand a programming task to the code module -- a coding agent
        that reads and edits the text files in this conversation's folder --
        and wait for its report. Where the command sandbox is set up and
        commands are allowed and the user approves that once per task, it
        runs its code and tests in the sandbox, held to this folder. Elsewhere its
        commands are off, except plain listings and reads of the folder, so
        it can't run scripts, tests or builds, nor read an xlsx, docx or pdf;
        then run a script yourself with your own tools. Use it to write or fix
        code and text files across the folder. It sees nothing of this conversation,
        so `task` must be complete: the files, the rules, what to produce
        and where. Outside the sandbox the user approves its file changes as
        they come; the user watches it, and can stop it, in the Sub Agents
        panel. Only its
        report comes back, with the files it created or changed.

        To change or fix what an earlier code task produced -- the user's
        feedback on its work -- pass that task's id as `continue_task`: the
        code module carries on in the same thread, remembering what it did
        and seeing its own files, so `task` need only say what to change.
        Don't continue for unrelated work; start a new task.

        Args:
            description: a few plain words for the panel, e.g. "Clean the
                order export and total by region".
            task: the complete task -- files, rules, outputs; for a
                continuation, what to change.
            continue_task: the id of an earlier, finished code task of this
                conversation to carry on from, as its report gave it.
        """
        previous: SubAgentTask | None = None
        if continue_task.strip():
            previous, problem = _continuation(store, continue_task.strip(), host.thread_id)
            if problem:
                return problem
        try:
            model = codex_model(context.model(), context.service().custom_providers())
        except CodexUnavailable as exc:
            return (
                f"The code module can't take this task: {exc} The user can pick a model "
                "Codex can use in Settings > Code > Model for code."
            )
        record = SubAgentTask(
            task_id=uuid.uuid4().hex[:12],
            thread_id=host.thread_id,
            instructions="",
            prompt=task,
            tool_names="",
            description=description.strip() or task.strip().splitlines()[0][:80],
            status="running",
            started_at=datetime.now(UTC).isoformat(),
            model=f"codex:{model.model}",
            continues=previous.task_id if previous else "",
            codex_thread=previous.codex_thread if previous else "",
        )
        run = _Run(host, store, record, context, previous)
        # A fresh context, as spawn_agent's runner gets: LangChain keeps the
        # running call's config in contextvars.
        runner = asyncio.create_task(run.drive(), context=contextvars.Context())
        register_subagent_run(record.task_id, runner, lambda: list(run.entries))
        store.save(record)
        try:
            # The panel's badge and list learn of it now, not at the first update.
            await host.changed(record)
            await asyncio.shield(runner)
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is None or not current.cancelling():
                return _report(record)
            # The parent's turn is ending: a Stop stops this run too (the
            # session cancels it); a dropped connection leaves it running as
            # a background run whose report waits in the panel.
            if not runner.done() and not runner.cancelling():
                record.background = True
                store.save(record)
            raise
        return _report(record)

    return tool_metadata(run_code_task, risk_category="READ", category="subagents")
