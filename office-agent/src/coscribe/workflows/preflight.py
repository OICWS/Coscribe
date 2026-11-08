"""What a run checks before its first step: that every step can run here, and the values it
starts from -- its inputs and, for a task that remembers (decision 0034), what the last run
that finished kept."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ..workflow_spec import (
    AgentStep,
    BranchStep,
    ChoiceStep,
    LoopStep,
    ParallelStep,
    RunTaskStep,
    ToolStep,
    Workflow,
    child_lists,
    failure_policy,
    input_values,
    remembered_values,
    walk,
)
from .agent_step import CODE_TOOLS
from .step_work import StepContext

# Tools that need a person in the loop mid-call; a workflow asks through an
# approval step instead.
UNAVAILABLE_TOOLS = frozenset({"ask_user_question", "create_scheduled_task"})

NO_STEPS = "This workflow has no steps yet -- add some on its task page."


class WorkflowNotRunnable(ValueError):
    pass


def preflight(workflow: Workflow, ctx: StepContext) -> None:
    """Refuse a workflow that can't run here, before any step does."""
    if not workflow.steps:
        raise WorkflowNotRunnable(NO_STEPS)
    for placed in walk(workflow.every_step()):
        step, where = placed.step, f"step {placed.number}"
        if isinstance(step, ToolStep):
            if step.tool in UNAVAILABLE_TOOLS:
                raise WorkflowNotRunnable(f"{where}: {step.tool} can't be used in a workflow")
            if step.tool not in ctx.tools:
                raise WorkflowNotRunnable(f"{where}: there's no tool called {step.tool!r}")
        if isinstance(step, AgentStep):
            _agent_preflight(step, where, ctx)
        if isinstance(step, RunTaskStep) and ctx.tasks is None:
            raise WorkflowNotRunnable(f"{where}: another task can't be run from here")
        if isinstance(step, ParallelStep) and not all(lane.steps for lane in step.lanes):
            raise WorkflowNotRunnable(f"{where}: a lane has no steps yet")
        if isinstance(step, LoopStep) and not step.steps:
            raise WorkflowNotRunnable(f"{where}: the loop has no steps to repeat yet")
        if isinstance(step, (BranchStep, ChoiceStep)) and not any(s for _a, s in child_lists(step)):
            raise WorkflowNotRunnable(f"{where}: the branch has no steps on any path yet")
        policy = failure_policy(step)
        if policy is not None and policy.then == "steps" and not policy.steps:
            raise WorkflowNotRunnable(f"{where}: no steps run in its place yet if it fails")


def _agent_preflight(step: AgentStep, where: str, ctx: StepContext) -> None:
    if ctx.run_agent is None:
        raise WorkflowNotRunnable(f"{where}: agent steps can't run here")
    for tool in step.tools:
        if tool in UNAVAILABLE_TOOLS or tool in CODE_TOOLS:
            raise WorkflowNotRunnable(f"{where}: {tool} can't be used in a workflow")
        if tool not in ctx.tools:
            raise WorkflowNotRunnable(f"{where}: there's no tool called {tool!r}")


def starting_values(
    workflow: Workflow, given: dict[str, Any], memory: dict[str, Any] | None = None
) -> dict[str, Any]:
    """The inputs, and for a task that remembers, `memory` (what is kept, else each entry's
    `initial`, else blank like an optional input left empty) and `run` (when this run
    started)."""
    try:
        values = input_values(workflow.inputs, given, date.today())
    except ValueError as exc:
        raise WorkflowNotRunnable(str(exc)) from exc
    if workflow.memory:
        now = datetime.now().replace(microsecond=0)
        values |= remembered_values(workflow.memory, memory or {}, now)
    return values
