"""The steps of a task that remembers (decision 0034): one that keeps a value for the next run,
and a check that ends the run with nothing to do instead of failing it. What a run keeps is
only handed back with its outcome; the caller keeps it when the run finished, so a failed,
stopped or test run never moves the task's memory on."""

from __future__ import annotations

from typing import Any, Protocol

from ..workflow_spec import CheckStep, RememberStep, Workflow, memory_value, render_value
from .step_work import StepContext, StepFailed, StepRecord, now_text, preview, run_check

# The route a check takes when its conditions don't hold and it ends the run.
ENDED = "end"
NOTHING_TO_DO = "Nothing to do: the run ended here"


class _Builder(Protocol):
    ctx: StepContext
    workflow: Workflow

    async def emit(self, record: StepRecord) -> None: ...


async def remember(
    builder: _Builder, step: RememberStep, values: dict[str, Any], it: list[int]
) -> dict[str, Any]:
    started = now_text()
    kind = next(m.type for m in builder.workflow.memory if m.name == step.name)
    try:
        value = memory_value(step.name, kind, render_value(step.value, values))
    except ValueError as exc:
        await builder.emit(StepRecord(step.id, "failed", started, now_text(), error=str(exc),
                                      iteration=it))  # fmt: skip
        raise StepFailed(str(exc), step_id=step.id) from exc
    await builder.emit(StepRecord(step.id, "done", started, now_text(),
                                  output={"name": step.name, "value": preview(value)},
                                  iteration=it))  # fmt: skip
    return {"remembered": {step.name: value}, "attempts": {step.id: {"route": "ok"}}}


async def check_or_end(
    builder: _Builder, step: CheckStep, values: dict[str, Any], it: list[int]
) -> dict[str, Any]:
    started = now_text()
    try:
        checks = run_check(step, values)
    except StepFailed as exc:
        await builder.emit(StepRecord(step.id, "done", started, now_text(), checks=exc.checks,
                                      note=NOTHING_TO_DO, iteration=it))  # fmt: skip
        return {"attempts": {step.id: {"route": ENDED}}}
    await builder.emit(StepRecord(step.id, "done", started, now_text(), checks=checks,
                                  iteration=it))  # fmt: skip
    return {"attempts": {step.id: {"route": "ok"}}}
