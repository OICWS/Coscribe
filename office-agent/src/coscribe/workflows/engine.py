"""Runs a Workflow as a LangGraph StateGraph, one node per step, over the
same checkpointer as conversations -- so a run that stops (a failed step,
a pending approval, a crash) picks up exactly where it stopped:

- A branch is a node whose outgoing edge depends on its condition; a loop
  is a start node, a next-item node and a collect node the body cycles
  through, with each pass's position in state. So everything below holds
  inside a loop too, for the pass that stopped.

- After a failure, resume() re-runs only the failed step: LangGraph keeps
  that step as the checkpoint's next node, and earlier steps' results in
  state. retry_from() forks from an earlier step instead (a check failing
  because a model step returned bad data needs that model step re-run).
- An approval step pauses with interrupt(). LangGraph re-executes the whole
  node on resume, so an approval step does nothing else -- a side effect
  placed before an interrupt() would happen twice.

Every step reports its progress through on_step as it goes, for the run's
record and a watching tab; the full values stay in the checkpoint."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import get_runtime
from langgraph.types import Command, interrupt

from ..needs_permission import NeedsPermission
from ..workflow_spec import (
    AgentStep,
    ApprovalStep,
    BranchStep,
    CheckStep,
    LLMStep,
    LoopStep,
    Placed,
    ScriptStep,
    Step,
    ToolStep,
    Workflow,
    evaluate,
    render_text,
    render_value,
    resolve,
    step_output,
    walk,
)
from .agent_step import CODE_TOOLS, AgentCall, AgentRunner, answer_of, run_agent_step
from .connector_value import connector_value as _connector_value
from .healing import carried, healed, stand_in
from .loop_labels import item_labels as _item_labels
from .loop_labels import loop_progress as _loop_progress
from .loop_labels import supersteps as _supersteps
from .model_step import ask_model, field_problems
from .permissions import untrusted_agent_steps

logger = logging.getLogger(__name__)

StepStatus = Literal["pending", "running", "done", "failed", "skipped", "waiting"]
RunOutcomeStatus = Literal["completed", "failed", "waiting"]

# Tools that need a person in the loop mid-call; a workflow asks through an
# approval step instead.
UNAVAILABLE_TOOLS = frozenset({"ask_user_question", "create_scheduled_task"})
SCRIPT_TIMEOUT_SECONDS = 300.0
_PREVIEW_TEXT_CHARS = 2000
_PREVIEW_LIST_ITEMS = 50

LLM_STEP_INSTRUCTIONS = (
    "You are one step of a fixed workflow, not a chat. Work only from the "
    "information given in the message. Return exactly the requested fields, "
    "with the requested types -- nothing else."
)


class StepFailed(Exception):
    def __init__(
        self, message: str, checks: list[dict[str, Any]] | None = None, step_id: str | None = None
    ) -> None:
        super().__init__(message)
        self.checks = checks
        self.step_id = step_id


class WorkflowNotRunnable(ValueError):
    pass


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    # The task's approval mode, which high and full agent steps run under.
    approval_mode: str = "manual"
    # Tools whose results come from outside: an agent step that reads one
    # through its references gets read-only tools.
    outside_tools: frozenset[str] = frozenset()


@dataclass
class RunOutcome:
    status: RunOutcomeStatus
    step_id: str | None = None
    error: str | None = None
    # For "waiting": what the approval step asks.
    request: dict[str, Any] | None = None
    values: dict[str, Any] = field(default_factory=dict)


OnStep = Callable[[StepRecord], Awaitable[None] | None]


def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def _merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {**left, **right}


class _State(TypedDict):
    values: Annotated[dict[str, Any], _merge]
    # Per loop id: {"index", "items", "results", "started_at"} of its
    # current pass.
    loops: Annotated[dict[str, Any], _merge]
    # Per step id: how it was last healed in this run (decision 0030), for its later passes.
    healed: Annotated[dict[str, Any], _merge]


def _node_name(step: Step) -> str:
    # A node can't share a name with a state key ("values").
    return f"step__{step.id}"


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


async def _run_tool(step: ToolStep, values: dict[str, Any], ctx: StepContext) -> Any:
    tool = ctx.tools[step.tool]
    args = render_value(step.args, values)
    if isinstance(tool, BaseTool):
        return _connector_value(await tool.ainvoke(args))
    if inspect.iscoroutinefunction(tool):
        result = await tool(**args)
    else:
        result = await asyncio.to_thread(tool, **args)
    _refuse_blocked_write(result)
    return result


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


async def _run_script(step: ScriptStep, values: dict[str, Any], ctx: StepContext) -> Any:
    inputs = render_value(step.inputs, values)
    # repr() of the JSON text is a valid Python string literal, so input
    # values can never break out into the script's code.
    prelude = f"inputs = __import__('json').loads({json.dumps(inputs, ensure_ascii=False)!r})\n"
    if ctx.run_script is not None:
        result = await asyncio.to_thread(
            ctx.run_script,
            ctx.workspace_root,
            ctx.state_dir,
            prelude + step.code,
            SCRIPT_TIMEOUT_SECONDS,
        )
    else:
        result = await asyncio.to_thread(
            _default_run_script,
            ctx.workspace_root,
            ctx.state_dir,
            prelude + step.code,
            SCRIPT_TIMEOUT_SECONDS,
            ctx.extra_writable,
        )
    _refuse_blocked_write(result)
    stderr = str(result.get("stderr") or "").strip()
    if result.get("timed_out"):
        raise StepFailed(
            f"The script ran longer than {SCRIPT_TIMEOUT_SECONDS:.0f}s and was stopped."
        )
    if result.get("exit_code") != 0:
        raise StepFailed(
            f"The script failed (exit code {result.get('exit_code')}): {stderr[-1500:]}"
        )
    lines = [line for line in str(result.get("stdout") or "").splitlines() if line.strip()]
    if not lines:
        raise StepFailed(
            "The script printed nothing; it must print its result as JSON on its last line."
        )
    try:
        return json.loads(lines[-1])
    except ValueError as exc:
        raise StepFailed(f"The script's last line isn't JSON: {lines[-1][:200]!r}") from exc


async def _run_llm(step: LLMStep, values: dict[str, Any], ctx: StepContext) -> Any:
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


def _run_check(step: CheckStep, values: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for condition in step.conditions:
        held, left, right = evaluate(condition, values)
        results.append({"held": held, "left": preview(left), "right": preview(right)})
    failed = [r for r in results if not r["held"]]
    if failed:
        raise StepFailed(f"{len(failed)} of {len(results)} checks failed", checks=results)
    return results


_NO_STEPS = "This workflow has no steps yet -- add some on its task page."


def preflight(workflow: Workflow, ctx: StepContext) -> None:
    """Refuse a workflow that can't run here, before any step does."""
    if not workflow.steps:
        raise WorkflowNotRunnable(_NO_STEPS)
    for placed in walk(workflow.steps):
        step, where = placed.step, f"step {placed.number}"
        if isinstance(step, ToolStep):
            if step.tool in UNAVAILABLE_TOOLS:
                raise WorkflowNotRunnable(f"{where}: {step.tool} can't be used in a workflow")
            if step.tool not in ctx.tools:
                raise WorkflowNotRunnable(f"{where}: there's no tool called {step.tool!r}")
        if isinstance(step, AgentStep):
            _agent_preflight(step, where, ctx)
        if isinstance(step, LoopStep) and not step.steps:
            raise WorkflowNotRunnable(f"{where}: the loop has no steps to repeat yet")
        if isinstance(step, BranchStep) and not (step.then or step.otherwise):
            raise WorkflowNotRunnable(f"{where}: the branch has no steps on either side yet")


def _agent_preflight(step: AgentStep, where: str, ctx: StepContext) -> None:
    if ctx.run_agent is None:
        raise WorkflowNotRunnable(f"{where}: agent steps can't run here")
    for tool in step.tools:
        if tool in UNAVAILABLE_TOOLS or tool in CODE_TOOLS:
            raise WorkflowNotRunnable(f"{where}: {tool} can't be used in a workflow")
        if tool not in ctx.tools:
            raise WorkflowNotRunnable(f"{where}: there's no tool called {tool!r}")


def resolve_inputs(workflow: Workflow, given: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for spec in workflow.inputs:
        value = given.get(spec.name, spec.default)
        if value is None or value == "":
            if not spec.required:
                values[spec.name] = ""
                continue
            raise WorkflowNotRunnable(f"input {spec.name!r} needs a value")
        values[spec.name] = value
    return values


class _GraphBuilder:
    def __init__(self, workflow: Workflow, ctx: StepContext, on_step: OnStep) -> None:
        self.workflow = workflow
        self.ctx = ctx
        self.on_step = on_step
        self.placed = {p.step.id: p for p in walk(workflow.steps)}
        self.read_only = set(untrusted_agent_steps(workflow, ctx.outside_tools))
        self.graph = StateGraph(_State)

    async def emit(self, record: StepRecord) -> None:
        result = self.on_step(record)
        if inspect.isawaitable(result):
            await result

    def iteration(self, state: _State, step: Step) -> list[int]:
        loops = state.get("loops") or {}
        return [loops[loop_id]["index"] for loop_id in self.placed[step.id].loops]

    async def fail(self, step: Step, it: list[int], started: str, exc: Exception) -> StepFailed:
        if isinstance(exc, StepFailed):
            failure = exc
        else:
            failure = StepFailed(str(exc) or type(exc).__name__)
        failure.step_id = step.id
        await self.emit(
            StepRecord(
                step.id,
                "failed",
                started,
                _now(),
                error=str(failure),
                checks=failure.checks,
                iteration=it,
            )
        )
        return failure

    def make_node(self, step: Step) -> Callable[[_State], Awaitable[dict[str, Any]]]:
        async def run(state: _State) -> dict[str, Any]:
            values = state["values"]
            it = self.iteration(state, step)
            started = _now()
            if isinstance(step, ApprovalStep):
                return await self._approval(step, values, started, it)
            await self.emit(StepRecord(step.id, "running", started_at=started, iteration=it))
            try:
                earlier = (state.get("healed") or {}).get(step.id)
                output, checks, agent = await self._try(step, values, started, it, earlier)
            except GraphBubbleUp:
                raise
            except Exception as exc:  # noqa: BLE001 -- any step error stops the run, recorded
                failure = await self.fail(step, it, started, exc)
                if failure is exc:
                    raise
                raise failure from exc
            await self.emit(
                StepRecord(
                    step.id,
                    "done",
                    started,
                    _now(),
                    output=preview(output),
                    checks=checks,
                    iteration=it,
                    agent=agent,
                )
            )
            save_as = None if isinstance(step, BranchStep) else step_output(step)
            heal = {"healed": {step.id: agent["healed"]}} if agent and "healed" in agent else {}
            return {"values": {save_as: output} if save_as else {}, **heal}

        return run

    async def _try(
        self, step: Step, values: dict[str, Any], started: str, it: list[int], earlier: Any
    ) -> tuple[Any, list[dict[str, Any]] | None, dict[str, Any] | None]:
        """A step's attempt, asking for what it needs; a failed browser step is healed when the
        task's autonomy allows it (decision 0030), and a later pass first tries what healed it.
        On resume after a pause in healing the step runs again from its start, and a step that
        still fails finds its agent where it was."""
        again = carried(step, earlier)
        try:
            while True:
                try:
                    if again is not None:
                        output, _, _ = await self._attempt(again, values, started, it)
                        return output, None, {"healed": {**earlier, "carried": True}}
                    return await self._attempt(step, values, started, it)
                except NeedsPermission as need:
                    if not self.ctx.ask_permission:
                        raise
                    await self._permission(step, need, started, it)
        except (GraphBubbleUp, NeedsPermission):
            raise
        except Exception as exc:
            error = str(exc) or type(exc).__name__
            agent_step = stand_in(self.workflow, step, values, error, earlier)
            if agent_step is None or self.ctx.run_agent is None:
                raise
            confirm = bool(getattr(step, "irreversible", False))
            try:
                result, agent = await self._agent(agent_step, values, started, it, confirm)
            except GraphBubbleUp:
                raise
            except Exception as heal_exc:
                raise StepFailed(f"{error} -- healing it didn't work: {heal_exc}") from heal_exc
            output, deviation = healed(step, result, error)
            return output, None, {**agent, "healed": deviation}

    async def _attempt(
        self, step: Step, values: dict[str, Any], started: str, it: list[int]
    ) -> tuple[Any, list[dict[str, Any]] | None, dict[str, Any] | None]:
        """One try at a step: its output, its checks and its agent's activity."""
        if isinstance(step, ToolStep):
            return await _run_tool(step, values, self.ctx), None, None
        if isinstance(step, ScriptStep):
            return await _run_script(step, values, self.ctx), None, None
        if isinstance(step, LLMStep):
            return await _run_llm(step, values, self.ctx), None, None
        if isinstance(step, AgentStep):
            output, agent = await self._agent(step, values, started, it)
            return output, None, agent
        if isinstance(step, CheckStep):
            return None, _run_check(step, values), None
        if isinstance(step, BranchStep):
            held, left, right = evaluate(step.condition, values)
            checks = [{"held": held, "left": preview(left), "right": preview(right)}]
            return {"arm": "then" if held else "otherwise"}, checks, None
        return None, None, None

    async def _agent(
        self, step: AgentStep, values: dict[str, Any], started: str, it: list[int],
        confirm: bool = False,
    ) -> tuple[Any, dict[str, Any]]:  # fmt: skip
        async def ask(call: AgentCall) -> dict[str, Any]:
            message = f"{step.title}: the agent wants to use {call.tool}."
            pending = {"pending": {"tool": call.tool, "args": preview(call.args)}}
            try:
                answer = interrupt({"step_id": step.id, "title": step.title, "message": message,
                                    "call_id": call.call_id, **pending})  # fmt: skip
            except GraphBubbleUp:
                # Only a real pause shows: on resume, earlier answers replay here.
                waiting = StepRecord(step.id, "waiting", started, output=message, iteration=it)
                await self.emit(replace(waiting, agent=pending))
                raise
            await self.emit(StepRecord(step.id, "running", started_at=started, iteration=it))
            return answer_of(answer)

        assert self.ctx.run_agent is not None  # preflight refuses a run without one
        info = get_runtime().execution_info
        assert info is not None  # set for every node LangGraph runs
        result, reply = await run_agent_step(
            step,
            values,
            self.ctx.run_agent,
            # One agent per pass of the step: the same across a pause, a new
            # one when the step is retried from an earlier checkpoint.
            key=f"workflow-agent-{info.task_id}",
            read_only=step.id in self.read_only,
            approval_mode=self.ctx.approval_mode,
            workspace=str(self.ctx.workspace_root),
            make_model=self.ctx.make_model,
            ask=ask,
            confirm_changes=confirm,
        )
        return result, reply.activity()

    async def _permission(
        self, step: Step, need: NeedsPermission, started: str, it: list[int]
    ) -> None:
        """Stop at a step that needs something the person hasn't allowed,
        and go on once they say yes. The step runs again from its start
        when the run resumes, so the allowance is recorded before that."""
        request = need.to_dict()
        await self.emit(
            StepRecord(
                step.id,
                "waiting",
                started,
                output=need.message,
                permission=request,
                iteration=it,
            )
        )
        answer = interrupt(
            {
                "step_id": step.id,
                "title": step.title,
                "message": need.message,
                "permission": request,
            }
        )
        if not (isinstance(answer, dict) and answer.get("approved") is True):
            raise StepFailed(f"Not allowed: {need.message}", step_id=step.id)
        await self.emit(StepRecord(step.id, "running", started_at=started, iteration=it))

    async def _approval(
        self, step: ApprovalStep, values: dict[str, Any], started: str, it: list[int]
    ) -> dict[str, Any]:
        checks = None
        if step.when is not None:
            held, left, right = evaluate(step.when, values)
            checks = [{"held": held, "left": preview(left), "right": preview(right)}]
            if not held:
                await self.emit(
                    StepRecord(step.id, "skipped", started, _now(), checks=checks, iteration=it)
                )
                return {"values": {}}
        message = render_text(step.message, values)
        await self.emit(
            StepRecord(step.id, "waiting", started, output=message, checks=checks, iteration=it)
        )
        answer = interrupt({"step_id": step.id, "title": step.title, "message": message})
        approved = isinstance(answer, dict) and answer.get("approved") is True
        note = str(answer.get("note") or "") if isinstance(answer, dict) else ""
        if not approved:
            error = "Not approved" + (f": {note}" if note else "")
            await self.emit(
                StepRecord(
                    step.id,
                    "failed",
                    started,
                    _now(),
                    output=message,
                    error=error,
                    note=note or None,
                    iteration=it,
                )
            )
            raise StepFailed(error, step_id=step.id)
        await self.emit(
            StepRecord(
                step.id,
                "done",
                started,
                _now(),
                output=message,
                note=note or None,
                iteration=it,
            )
        )
        return {"values": {}}

    def loop_start(self, step: LoopStep) -> Callable[[_State], Awaitable[dict[str, Any]]]:
        async def run(state: _State) -> dict[str, Any]:
            it = self.iteration(state, step)
            started = _now()
            try:
                items = resolve(step.over, state["values"])
                if not isinstance(items, list):
                    raise StepFailed(
                        f"{step.over} is {type(items).__name__}, not a list to go through"
                    )
                if len(items) > step.max_items:
                    raise StepFailed(
                        f"{step.over} has {len(items)} items, more than this loop's limit of "
                        f"{step.max_items}"
                    )
            except Exception as exc:  # noqa: BLE001 -- recorded like any step's failure
                failure = await self.fail(step, it, started, exc)
                if failure is exc:
                    raise
                raise failure from exc
            loop = {
                "index": 0,
                "items": items,
                "labels": _item_labels(items),
                "results": [],
                "started_at": started,
            }
            await self.emit(
                StepRecord(step.id, "running", started, output=_loop_progress(loop), iteration=it)
            )
            return {"loops": {step.id: loop}}

        return run

    def loop_next(self, step: LoopStep) -> Callable[[_State], Awaitable[dict[str, Any]]]:
        async def run(state: _State) -> dict[str, Any]:
            loop = state["loops"][step.id]
            if loop["index"] < len(loop["items"]):
                return {"values": {step.item: loop["items"][loop["index"]]}}
            output = {**_loop_progress(loop), "collected": preview(loop["results"])}
            await self.emit(
                StepRecord(
                    step.id,
                    "done",
                    loop["started_at"],
                    _now(),
                    output=output,
                    iteration=self.iteration(state, step),
                )
            )
            return {"values": {step.save_as: loop["results"]}} if step.save_as else {"values": {}}

        return run

    def loop_collect(self, step: LoopStep) -> Callable[[_State], Awaitable[dict[str, Any]]]:
        async def run(state: _State) -> dict[str, Any]:
            loop = state["loops"][step.id]
            it = self.iteration(state, step)
            try:
                value = resolve(step.collect, state["values"]) if step.collect else None
            except Exception as exc:  # noqa: BLE001 -- recorded like any step's failure
                failure = await self.fail(step, it, loop["started_at"], exc)
                if failure is exc:
                    raise
                raise failure from exc
            loop = {**loop, "index": loop["index"] + 1, "results": [*loop["results"], value]}
            await self.emit(
                StepRecord(
                    step.id,
                    "running",
                    loop["started_at"],
                    output=_loop_progress(loop),
                    iteration=it,
                )
            )
            return {"loops": {step.id: loop}}

        return run

    def wire(self, steps: list[Step], after: str) -> None:
        for index, step in enumerate(steps):
            following = _node_name(steps[index + 1]) if index + 1 < len(steps) else after
            node = _node_name(step)
            if isinstance(step, BranchStep):
                self.graph.add_node(node, cast(Any, self.make_node(step)))
                self.graph.add_conditional_edges(
                    node,
                    _branch_router(step),
                    {
                        "then": _node_name(step.then[0]) if step.then else following,
                        "otherwise": _node_name(step.otherwise[0]) if step.otherwise else following,
                    },
                )
                self.wire(step.then, following)
                self.wire(step.otherwise, following)
            elif isinstance(step, LoopStep):
                next_node, collect_node = f"next__{step.id}", f"collect__{step.id}"
                self.graph.add_node(node, cast(Any, self.loop_start(step)))
                self.graph.add_node(next_node, cast(Any, self.loop_next(step)))
                self.graph.add_node(collect_node, cast(Any, self.loop_collect(step)))
                self.graph.add_edge(node, next_node)
                self.graph.add_conditional_edges(
                    next_node,
                    _loop_router(step),
                    {
                        "body": _node_name(step.steps[0]) if step.steps else collect_node,
                        "done": following,
                    },
                )
                self.wire(step.steps, collect_node)
                self.graph.add_edge(collect_node, next_node)
            else:
                self.graph.add_node(node, cast(Any, self.make_node(step)))
                self.graph.add_edge(node, following)

    def build(self, checkpointer: Any) -> Any:
        self.wire(self.workflow.steps, END)
        self.graph.add_edge(START, _node_name(self.workflow.steps[0]))
        return self.graph.compile(checkpointer=checkpointer)


def build_graph(workflow: Workflow, ctx: StepContext, on_step: OnStep, checkpointer: Any) -> Any:
    return _GraphBuilder(workflow, ctx, on_step).build(checkpointer)


def _branch_router(step: BranchStep) -> Callable[[_State], str]:
    # Re-evaluating is safe: the branch node already evaluated the same
    # values without error, and nothing has changed them since.
    def route(state: _State) -> str:
        held, _left, _right = evaluate(step.condition, state["values"])
        return "then" if held else "otherwise"

    return route


def _loop_router(step: LoopStep) -> Callable[[_State], str]:
    def route(state: _State) -> str:
        loop = state["loops"][step.id]
        return "body" if loop["index"] < len(loop["items"]) else "done"

    return route


class WorkflowRun:
    """One run of a workflow, on its own checkpoint thread."""

    def __init__(
        self,
        workflow: Workflow,
        ctx: StepContext,
        checkpointer: Any,
        thread_id: str,
        on_step: OnStep,
    ) -> None:
        self.workflow = workflow
        self.ctx = ctx
        self.on_step = on_step
        self._placed: dict[str, Placed] = {p.step.id: p for p in walk(workflow.steps)}
        self.config: dict[str, Any] = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": _supersteps(workflow.steps) + 10,
        }
        self._graph = build_graph(workflow, ctx, on_step, checkpointer) if workflow.steps else None

    async def start(self, inputs: dict[str, Any]) -> RunOutcome:
        preflight(self.workflow, self.ctx)
        return await self._drive({"values": resolve_inputs(self.workflow, inputs), "loops": {}})

    async def resume(self) -> RunOutcome:
        """Carry on after a crash or a failed step's cause being fixed. A
        declined approval stays declined here -- LangGraph replays the
        recorded answer -- so asking again is retry_from() that step."""
        return await self._drive(None)

    async def answer(self, approved: bool, note: str = "") -> RunOutcome:
        # An agent step's answer names its call: resuming replays earlier
        # answers by position, and the agent must not take one for another.
        state = await self._compiled.aget_state(self.config)
        asked = [i.value for t in state.tasks for i in t.interrupts if isinstance(i.value, dict)]
        call_id = asked[0].get("call_id") if asked else None
        return await self._drive(
            Command(resume={"approved": approved, "note": note, "call_id": call_id})
        )

    async def retry_from(self, step_id: str) -> RunOutcome:
        """Re-run from an earlier step, discarding what came after it --
        inside a loop, from that step's most recent pass."""
        target = f"step__{step_id}"
        async for snapshot in self._compiled.aget_state_history(self.config):
            if snapshot.next == (target,):
                config = {**snapshot.config, "recursion_limit": self.config["recursion_limit"]}
                return await self._drive(None, config)
        raise WorkflowNotRunnable(f"step {step_id!r} hasn't been reached in this run")

    @property
    def _compiled(self) -> Any:
        if self._graph is None:
            raise WorkflowNotRunnable(_NO_STEPS)
        return self._graph

    async def _emit(self, record: StepRecord) -> None:
        result = self.on_step(record)
        if inspect.isawaitable(result):
            await result

    def _loops_around(self, node: str) -> tuple[str, ...]:
        kind, _, step_id = node.partition("__")
        placed = self._placed.get(step_id)
        if placed is None:
            return ()
        # A loop's own next-item and collect nodes are inside it.
        return (*placed.loops, step_id) if kind in ("next", "collect") else placed.loops

    async def _mark_loops(
        self,
        node: str,
        status: StepStatus,
        error: str | None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Record the loops around a stopped (or resuming) step as stopped
        (or running) at that pass, so a loop's own row says where it is."""
        around = self._loops_around(node)
        if not around:
            return
        state = await self._compiled.aget_state(config or self.config)
        loops = (state.values or {}).get("loops") or {}
        for depth, loop_id in enumerate(around):
            loop = loops.get(loop_id)
            if loop is None:
                continue
            await self._emit(
                StepRecord(
                    loop_id,
                    status,
                    loop["started_at"],
                    output=_loop_progress(loop),
                    error=error and f"Stopped at item {loop['index'] + 1}: {error}",
                    iteration=[loops[outer]["index"] for outer in around[:depth]],
                )
            )

    async def _drive(self, payload: Any, config: dict[str, Any] | None = None) -> RunOutcome:
        graph = self._compiled
        if payload is None or isinstance(payload, Command):
            state = await graph.aget_state(config or self.config)
            for node in state.next:
                await self._mark_loops(node, "running", None, config)
        try:
            await graph.ainvoke(payload, config or self.config)
        except StepFailed as exc:
            await self._mark_loops(f"step__{exc.step_id}", "failed", str(exc))
            state = await graph.aget_state(self.config)
            return RunOutcome(
                "failed", step_id=exc.step_id, error=str(exc), values=state.values.get("values", {})
            )
        state = await graph.aget_state(self.config)
        values = state.values.get("values", {})
        for task in state.tasks:
            for pending in task.interrupts:
                request = pending.value if isinstance(pending.value, dict) else {}
                await self._mark_loops(f"step__{request.get('step_id')}", "waiting", None)
                return RunOutcome(
                    "waiting", step_id=request.get("step_id"), request=request, values=values
                )
        return RunOutcome("completed", values=values)
