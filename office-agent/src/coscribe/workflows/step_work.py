"""What a work step does when it runs -- a tool, a script, a model, a check -- and what the
engine hands it: the run's context, and the failure a step raises."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from ..needs_permission import NeedsPermission
from ..workflow_spec import (
    MAX_RETRY_WAIT,
    CheckStep,
    LLMStep,
    ScriptStep,
    ToolStep,
    conditions_hold,
    render_text,
    render_value,
)
from .agent_step import AgentRunner
from .connector_value import connector_value as _connector_value
from .model_step import ask_model, field_problems

if TYPE_CHECKING:
    from .run_task import TaskSource

SCRIPT_TIMEOUT_SECONDS = 300.0
SCRIPT_TOOLS = frozenset({"run_python_script", "run_node_script"})
_PREVIEW_TEXT_CHARS = 2000
_PREVIEW_LIST_ITEMS = 50

LLM_STEP_INSTRUCTIONS = (
    "You are one step of a fixed workflow, not a chat. Work only from the "
    "information given in the message. Return exactly the requested fields, "
    "with the requested types -- nothing else."
)


StepStatus = Literal["pending", "running", "done", "failed", "skipped", "waiting"]


def now_text() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


@dataclass
class StepRecord:
    step_id: str
    status: StepStatus
    started_at: str | None = None
    finished_at: str | None = None
    output: Any = None
    error: str | None = None
    # One entry per condition of a check (or an approval's `when`):
    # {"held", "left", "right"}, so a failure shows what it compared.
    checks: list[dict[str, Any]] | None = None
    # What the person who answered an approval step wrote, if anything.
    note: str | None = None
    # Which pass of each loop around the step this is, outermost first --
    # empty outside loops. A step's record is one per pass.
    iteration: list[int] = field(default_factory=list)
    # A waiting step that is asking to be allowed something, not approved:
    # {"kind": "folder" | "site", "target", "message"}.
    permission: dict[str, Any] | None = None
    # An agent step's work: {"tool_calls", "tokens", "tools_used"} once it
    # ends, {"pending": {"tool", "args"}} while a call waits for a person.
    agent: dict[str, Any] | None = None
    # Tries the step took in this pass (decision 0032); more than one only when it has retries.
    attempts: int = 1
    # A failed step whose failure didn't stop the run: it was skipped, steps ran in its place, its
    # loop skipped the item it failed on, or the run added steps for it (decision 0042).
    recovered: Literal["skipped", "fallback", "item_skipped", "added"] | None = None
    # A waiting ask or wait step, and what for (decision 0033): conversation.wire's WorkflowPause.
    pause: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StepFailed(Exception):
    def __init__(
        self,
        message: str,
        checks: list[dict[str, Any]] | None = None,
        step_id: str | None = None,
        *,
        declined: bool = False,
    ) -> None:
        super().__init__(message)
        self.checks = checks
        self.step_id = step_id
        # A person said no: trying again would ask them again, and they know the run stopped.
        self.declined = declined


@dataclass
class StepContext:
    # Built-in tools are plain functions; a connector's are LangChain tools.
    tools: dict[str, Any]
    workspace_root: Path
    state_dir: Path
    # A LangChain chat model for a "provider:model" string, or the
    # default model for None.
    make_model: Callable[[str | None], Any]
    run_script: Callable[[Path, Path, str, float], dict[str, object]] | None = None
    # The folders a script may write besides the workspace.
    extra_writable: Sequence[Path] = ()
    # A saved run waits for the person when a step needs a folder or site
    # it hasn't been allowed; anywhere else that is an ordinary failure.
    ask_permission: bool = False
    # Runs agent steps (decision 0028); without one a workflow that has
    # one is refused before it starts.
    run_agent: AgentRunner | None = None
    # A wait step waits; a test run's looks for its file once and goes on (decision 0033).
    waits: bool = True
    # The task's approval mode, which high and full agent steps run under.
    approval_mode: str = "manual"
    # Tools whose results come from outside: an agent step that reads one
    # through its references gets read-only tools.
    outside_tools: frozenset[str] = frozenset()
    # The longest wait between a step's tries (decision 0032): a test run shortens it.
    max_retry_wait: float = float(MAX_RETRY_WAIT)
    # The tasks a run-task step may run (decision 0035); without it such a step fails.
    tasks: TaskSource | None = None
    # The tools that only read: a step a run adds in front of any other waits for a person
    # (decision 0042). Empty means every tool asks.
    read_tools: frozenset[str] = frozenset()
    # On where a model can plan them; off inside a called task, a parallel lane and the steps a
    # run added, so those never add more.
    adds_steps: bool = False


def preview(value: Any, depth: int = 0) -> Any:
    """A bounded, JSON-safe copy for a run record."""
    if isinstance(value, str):
        if len(value) <= _PREVIEW_TEXT_CHARS:
            return value
        return (
            value[:_PREVIEW_TEXT_CHARS]
            + f"... [{len(value) - _PREVIEW_TEXT_CHARS} more characters]"
        )
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if depth > 4:
        return "..."
    if isinstance(value, dict):
        return {str(k): preview(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        items = [preview(v, depth + 1) for v in value[:_PREVIEW_LIST_ITEMS]]
        if len(value) > _PREVIEW_LIST_ITEMS:
            items.append(f"... [{len(value) - _PREVIEW_LIST_ITEMS} more items]")
        return items
    return str(value)


async def run_tool(step: ToolStep, values: dict[str, Any], ctx: StepContext) -> Any:
    tool = ctx.tools[step.tool]
    args = render_value(step.args, values)
    if isinstance(tool, BaseTool):
        return _connector_value(await tool.ainvoke(args))
    if inspect.iscoroutinefunction(tool):
        result = await tool(**args)
    else:
        result = await asyncio.to_thread(tool, **args)
    _refuse_blocked_write(result)
    if step.tool in SCRIPT_TOOLS and isinstance(result, dict):
        _refuse_failed_script(result)
    return result


def _refuse_failed_script(result: dict[str, Any]) -> None:
    """A script that threw or ran too long fails its step. Called as a tool, the call itself
    returns normally, so a check the script raised would otherwise let the run carry on."""
    if result.get("timed_out"):
        raise StepFailed("The script ran too long and was stopped.")
    if result.get("exit_code") != 0:
        stderr = str(result.get("stderr") or "").strip()[-1500:]
        raise StepFailed(f"The script failed (exit code {result.get('exit_code')}): {stderr}")


def _refuse_blocked_write(result: Any) -> None:
    """A script the folder guard stopped is a step that needs a folder."""
    if isinstance(result, dict) and result.get("blocked_write"):
        path = str(result["blocked_write"])
        folder = str(result.get("blocked_folder") or "")
        raise NeedsPermission(
            "folder",
            folder or path,
            f'The script tried to write "{path}", which is outside the workspace and the '
            "folders this run may use. Allow that folder, or have the script save inside "
            "the workspace.",
        )


def _default_run_script(
    workspace_root: Path,
    state_dir: Path,
    script: str,
    timeout: float,
    extra_writable: Sequence[Path] = (),
) -> dict[str, object]:
    from ..tools import run_python_script

    return run_python_script(workspace_root, state_dir, script, timeout, extra_writable)


async def run_script(step: ScriptStep, values: dict[str, Any], ctx: StepContext) -> Any:
    inputs = render_value(step.inputs, values)
    # repr() of the JSON text is a valid Python string literal, so input
    # values can never break out into the script's code.
    prelude = f"inputs = __import__('json').loads({json.dumps(inputs, ensure_ascii=False)!r})\n"
    where = (ctx.workspace_root, ctx.state_dir, prelude + step.code, SCRIPT_TIMEOUT_SECONDS)
    if ctx.run_script is not None:
        result = await asyncio.to_thread(ctx.run_script, *where)
    else:
        result = await asyncio.to_thread(_default_run_script, *where, ctx.extra_writable)
    _refuse_blocked_write(result)
    _refuse_failed_script(result)
    lines = [line for line in str(result.get("stdout") or "").splitlines() if line.strip()]
    if not lines:
        raise StepFailed(
            "The script printed nothing; it must print its result as JSON on its last line."
        )
    try:
        return json.loads(lines[-1])
    except ValueError as exc:
        raise StepFailed(f"The script's last line isn't JSON: {lines[-1][:200]!r}") from exc


async def run_llm(step: LLMStep, values: dict[str, Any], ctx: StepContext) -> Any:
    model = ctx.make_model(step.model)
    if "temperature" in getattr(type(model), "model_fields", {}):
        model = model.model_copy(update={"temperature": 0})
    field_lines = "\n".join(f"- {f.name} ({f.type}): {f.description}" for f in step.fields)
    messages: list[Any] = [
        SystemMessage(LLM_STEP_INSTRUCTIONS),
        HumanMessage(f"{render_text(step.prompt, values)}\n\nReturn:\n{field_lines}"),
    ]
    problems: list[str] = []
    for _attempt in range(2):
        try:
            result = await ask_model(model, messages, step.fields)
        except ValueError as exc:
            problems = [str(exc)]
        else:
            cleaned, problems = field_problems(result, step.fields)
            if not problems:
                return cleaned
        messages.append(
            HumanMessage("That result was rejected: " + "; ".join(problems) + ". Try again.")
        )
    raise StepFailed("The model didn't return the required fields: " + "; ".join(problems))


def checks_of(checked: list[tuple[bool, Any, Any]]) -> list[dict[str, Any]]:
    return [
        {"held": h, "left": preview(left), "right": preview(right)} for h, left, right in checked
    ]


def run_check(step: CheckStep, values: dict[str, Any]) -> list[dict[str, Any]]:
    held, checked = conditions_hold(step.conditions, step.match, values, step.match == "any")
    results = checks_of(checked)
    if not held:
        failed = f"{sum(not r['held'] for r in results)} of {len(results)} checks failed"
        raise StepFailed(
            "none of the checks held" if step.match == "any" else failed, checks=results
        )
    return results
