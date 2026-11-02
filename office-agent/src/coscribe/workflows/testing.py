"""A test run of a workflow: the real steps, once, reported step by step --
how the assistant checks a workflow it drafted or revised before the user
reviews it, and reproduces a saved one's failure.

It runs on a throwaway checkpointer, so nothing lands in a task's run
history, and stops before an approval step: a test has no one to ask, and
what comes after an approval is exactly what the approval guards. It also
stops before a step marked irreversible unless told to send for real
(decision 0029): checking a fix must not file a claim or pay an invoice. A
step's retries wait at most a few seconds between tries in a test (decision
0032): a test is waited for, and what it checks is the workflow, not how long
a site takes to come back. A wait step doesn't wait in a test, and an ask
step goes on with its defaults where it has them (decision 0033)."""

from __future__ import annotations

import contextlib
import csv
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from ..tools import browser_run
from ..workflow_spec import (
    AgentStep,
    ApprovalStep,
    BranchStep,
    ChoiceStep,
    LoopStep,
    Step,
    ToolStep,
    Workflow,
    failure_policy,
    walk,
)
from .engine import StepContext, StepRecord, WorkflowNotRunnable, WorkflowRun
from .step_work import preview

_OUTPUT_CHARS = 400
_MAX_FILES = 10
# Where a tool's result names a file it wrote, moved or downloaded.
_FILE_KEYS = frozenset({"path", "file", "files", "destination"})


def uses_browser(workflow: Workflow) -> bool:
    return any(
        isinstance(placed.step, ToolStep) and placed.step.tool.startswith("browser_")
        for placed in walk(workflow.every_step())
    )


def _seconds(record: StepRecord) -> float | None:
    if not record.started_at or not record.finished_at:
        return None
    try:
        start = datetime.fromisoformat(record.started_at)
        end = datetime.fromisoformat(record.finished_at)
    except ValueError:
        return None
    return round((end - start).total_seconds(), 1)


def _clip(value: Any) -> Any:
    shown = preview(value)
    text = shown if isinstance(shown, str) else json.dumps(shown, ensure_ascii=False, default=str)
    return text if len(text) <= _OUTPUT_CHARS else f"{text[:_OUTPUT_CHARS]}…"


def _named_files(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _FILE_KEYS and isinstance(item, str):
                found.append(item)
            elif key in _FILE_KEYS and isinstance(item, list):
                found += [x for x in item if isinstance(x, str)]
            else:
                found += _named_files(item)
    elif isinstance(value, list):
        for item in value:
            found += _named_files(item)
    return found


def _table_shape(path: Path) -> dict[str, int]:
    """Rows and columns of a spreadsheet's first sheet, or {} if it can't be read."""
    try:
        if path.suffix.lower() in {".xlsx", ".xlsm"}:
            from openpyxl import load_workbook

            book = load_workbook(path, read_only=True)
            try:
                sheet = book.worksheets[0]
                return {"rows": sheet.max_row or 0, "columns": sheet.max_column or 0}
            finally:
                book.close()
        if path.suffix.lower() == ".csv":
            with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
                rows = list(csv.reader(handle))
            return {"rows": len(rows), "columns": max((len(r) for r in rows), default=0)}
    except Exception:  # noqa: BLE001 -- a file that isn't a real table just shows no shape
        return {}
    return {}


def output_files(outputs: list[Any], root: Path, since: float) -> list[dict[str, Any]]:
    """Files the steps' results (`outputs`) name that were written during
    the run -- what a reviewer checks first."""
    files: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for output in outputs:
        for name in _named_files(output):
            path = (root / name).resolve() if not Path(name).is_absolute() else Path(name)
            if path in seen or not path.is_file() or path.stat().st_mtime < since:
                continue
            seen.add(path)
            try:
                shown = str(path.relative_to(root.resolve()))
            except ValueError:
                shown = str(path)
            files.append({"path": shown, "size": path.stat().st_size, **_table_shape(path)})
            if len(files) == _MAX_FILES:
                return files
    return files


_GUARD_PREFIX = "before_"
_TEST_RETRY_WAIT_SECONDS = 5


def _guarded(workflow: Workflow) -> tuple[Workflow, dict[str, Step]]:
    """The workflow with an approval step in front of every irreversible
    one -- the engine already stops a test there -- and which guard stands
    for which step."""
    taken = {placed.step.id for placed in walk(workflow.every_step())}
    guards: dict[str, Step] = {}

    def guard(step: Step) -> ApprovalStep:
        gid = _GUARD_PREFIX + step.id
        while gid in taken:
            gid += "_"
        taken.add(gid)
        guards[gid] = step
        return ApprovalStep(
            id=gid,
            title=f"Before {step.title}"[:120],
            message=f"{step.title} can't be taken back.",
        )

    def rebuild(steps: list[Step]) -> list[Step]:
        out: list[Step] = []
        for step in steps:
            if isinstance(step, LoopStep):
                step = step.model_copy(update={"steps": rebuild(step.steps)})
            elif isinstance(step, BranchStep):
                step = step.model_copy(
                    update={"then": rebuild(step.then), "otherwise": rebuild(step.otherwise)}
                )
            elif isinstance(step, ChoiceStep):
                cases = [c.model_copy(update={"steps": rebuild(c.steps)}) for c in step.cases]
                step = step.model_copy(
                    update={"cases": cases, "otherwise": rebuild(step.otherwise)}
                )
            policy = failure_policy(step)
            if policy is not None and policy.steps:
                in_place = policy.model_copy(update={"steps": rebuild(policy.steps)})
                step = step.model_copy(update={"on_failure": in_place})
            if isinstance(step, (ToolStep, AgentStep)) and step.irreversible:
                out.append(guard(step))
            out.append(step)
        return out

    # The steps after a failed run can't pause at a guard (decision 0032), so a test leaves out
    # the ones that can't be taken back.
    after = [s for s in workflow.after_failure if not getattr(s, "irreversible", False)]
    guarded = {"steps": rebuild(workflow.steps), "after_failure": after}
    return workflow.model_copy(update=guarded), guards


def _guard_only(workflow: Workflow) -> Workflow:
    return _guarded(workflow)[0]


def _stopped_inside(outcome: Any) -> dict[str, str] | None:
    """The step of a called task (decision 0035) a test stopped before, when it stopped at one
    of that task's guards: {"id", "title"}."""
    step_id = str(outcome.step_id or "")
    inner = step_id.rsplit("/", 1)[-1]
    if "/" not in step_id or not inner.startswith(_GUARD_PREFIX):
        return None
    title = str((outcome.request or {}).get("title") or "").removeprefix("Before ")
    return {"id": step_id.removesuffix(inner) + inner.removeprefix(_GUARD_PREFIX), "title": title}


async def run_test(
    workflow: Workflow,
    ctx: StepContext,
    inputs: dict[str, Any] | None = None,
    on_step: Callable[[StepRecord], Awaitable[None]] | None = None,
    thread_id: str = "",
    *,
    send_for_real: bool = False,
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """{"status": "passed" | "failed" | "stopped_at_approval" |
    "stopped_before_irreversible", "seconds", "steps": [{"id", "title",
    "status", "seconds", "output", "error"}], "failed_step", "error"} --
    every step listed, "not reached" for those the run never got to; with
    "stopped_before" ({"id", "title"}) when an irreversible step stopped it.
    `send_for_real` runs irreversible steps too. A task's `memory` is read as a run reads it;
    what the run would keep comes back as "would_remember", and "ended" says a check ended it
    with nothing to do (decision 0034) -- a test never keeps anything."""
    records: dict[str, StepRecord] = {}
    shown = workflow
    guards: dict[str, Step] = {}
    if not send_for_real:
        workflow, guards = _guarded(workflow)

    async def record_step(record: StepRecord) -> None:
        # Inside a loop the last pass stands for the step.
        records[record.step_id] = record
        if on_step is not None:
            await on_step(record)

    # A called task's steps that can't be taken back stop the test too, and it keeps nothing.
    tasks = ctx.tasks and replace(ctx.tasks, prepare=None if send_for_real else _guard_only,
                                  record=None, keeps=False)  # fmt: skip
    ctx = replace(ctx, max_retry_wait=min(ctx.max_retry_wait, _TEST_RETRY_WAIT_SECONDS),
                  waits=False, tasks=tasks)  # fmt: skip
    run = WorkflowRun(workflow, ctx, InMemorySaver(), f"test-{uuid.uuid4().hex[:8]}", record_step)
    started = time.monotonic()
    # Whole seconds: some file systems keep coarse modification times.
    started_at = int(time.time())
    lock = browser_run(thread_id) if uses_browser(workflow) else contextlib.nullcontext()
    async with lock:
        try:
            outcome = await run.start(inputs or {}, memory)
        except WorkflowNotRunnable as exc:
            return {
                "status": "failed",
                "seconds": 0.0,
                "steps": [],
                "files": [],
                "failed_step": None,
                "error": str(exc),
            }
    status = {"completed": "passed", "waiting": "stopped_at_approval"}.get(outcome.status, "failed")
    stopped_before = guards.get(outcome.step_id or "") if status == "stopped_at_approval" else None
    stopped_inside = _stopped_inside(outcome) if status == "stopped_at_approval" else None
    if stopped_before is not None or stopped_inside is not None:
        status = "stopped_before_irreversible"
    steps = []
    for placed in walk(shown.every_step()):
        record = records.get(placed.step.id)
        step: dict[str, Any] = {
            "id": placed.step.id,
            "title": placed.step.title,
            "status": record.status if record else "not reached",
            "seconds": _seconds(record) if record else None,
            "output": _clip(record.output) if record and record.output is not None else None,
            "error": record.error if record else None,
        }
        if record and record.status == "failed" and record.checks:
            step["checks"] = record.checks
        steps.append(step)
    extra: dict[str, Any] = (
        {"stopped_before": {"id": stopped_before.id, "title": stopped_before.title}}
        if stopped_before is not None
        else {"stopped_before": stopped_inside}
        if stopped_inside is not None
        else {}
    )
    if status == "passed" and outcome.ended:
        extra["ended"] = True
    if status == "passed" and outcome.remembered:
        extra["would_remember"] = {k: _clip(v) for k, v in outcome.remembered.items()}
    return {
        "status": status,
        **extra,
        "seconds": round(time.monotonic() - started, 1),
        "steps": steps,
        "files": output_files([r.output for r in records.values()], ctx.workspace_root, started_at),
        "failed_step": outcome.step_id if status == "failed" else None,
        "error": outcome.error if status == "failed" else None,
    }
