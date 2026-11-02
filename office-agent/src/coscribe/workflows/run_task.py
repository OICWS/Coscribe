"""A step that runs another task (decision 0035), as a run of its own inside the step: on its own
checkpoint thread in the caller's store, with its own approval mode, memory and steps after a
failure. Its records become the caller's, as `<step>/<its step>`, and its pauses pause the
caller: each is passed up with interrupt(), keyed by where the called run stopped, because
LangGraph replays every earlier answer when the step runs again and only the newest is for the
called run's current pause. The called run's thread is kept across the step's tries, so a retry
goes on from where it failed instead of doing again what it already did."""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any, Protocol

from langchain_core.runnables.config import var_child_runnable_config
from langgraph.config import get_config
from langgraph.errors import GraphBubbleUp
from langgraph.runtime import get_runtime
from langgraph.types import interrupt

from ..workflow_spec import MAX_TASK_DEPTH, RunTaskStep, Workflow, parse_workflow, render_value
from .step_work import StepContext, StepFailed, StepRecord, now_text, preview


@dataclass
class CalledTask:
    task_id: str
    name: str
    version: int | None
    workflow: Workflow
    approval_mode: str
    memory: dict[str, Any]


@dataclass
class TaskSource:
    """Where a run finds the tasks its steps run: the schedule store, and the run's record of
    which version of each it ran. `path` and `chain` say where in the calls this one is."""

    store: Any
    # (path, {"task", "name", "version", "workflow"}): the caller's run record keeps it.
    record: Callable[[str, dict[str, Any]], None] | None = None
    # A test run's guard in front of every step that can't be taken back.
    prepare: Callable[[Workflow], Workflow] | None = None
    # Who keeps what a called task remembers, for its memory page.
    by: str = "a run"
    # A test run keeps nothing.
    keeps: bool = True
    path: str = ""
    chain: tuple[str, ...] = field(default_factory=tuple)

    def load(self, step_id: str, task_id: str) -> CalledTask:
        if task_id in self.chain:
            raise StepFailed("This task is already running further up; tasks can't run in a circle")
        if len(self.chain) > MAX_TASK_DEPTH:
            raise StepFailed(f"Tasks run each other at most {MAX_TASK_DEPTH} deep")
        trigger = self.store.load(task_id)
        if trigger is None or trigger.workflow is None:
            raise StepFailed("The task this step runs no longer exists, or has no steps")
        version = self.store.versions.keep(task_id, trigger.workflow, "found")
        if self.record is not None:
            info = {"task": task_id, "name": trigger.name, "version": version}
            self.record(self.path + step_id, {**info, "workflow": trigger.workflow})
        workflow = parse_workflow(trigger.workflow)
        if self.prepare is not None:
            workflow = self.prepare(workflow)
        memory = self.store.memory.values(task_id)
        return CalledTask(task_id, trigger.name, version, workflow, trigger.approval_mode, memory)

    def below(self, step_id: str, task_id: str) -> TaskSource:
        return replace(self, path=f"{self.path}{step_id}/", chain=(*self.chain, task_id))

    def keep(self, task_id: str, remembered: dict[str, Any]) -> None:
        if self.keeps:
            self.store.memory.keep(task_id, remembered, self.by)


async def _alone(work: Awaitable[Any]) -> Any:
    """`work` outside the caller's graph, which would otherwise take the called run's graph for
    a part of its own; every other context (the run's session, its tools) carries over."""
    context = contextvars.copy_context()
    context.run(var_child_runnable_config.set, None)
    return await asyncio.create_task(_awaited(work), context=context)


async def _awaited(work: Awaitable[Any]) -> Any:
    return await work


class _Builder(Protocol):
    ctx: StepContext
    checkpointer: Any

    async def emit(self, record: StepRecord) -> None: ...

    async def recover(
        self, step: Any, state: Any, it: list[int], started: str, tries: int, exc: Exception
    ) -> dict[str, Any]: ...


class TaskSteps:
    """Runs the run-task steps of the graph builder that owns them."""

    def __init__(self, builder: _Builder, make_run: Callable[..., Any]) -> None:
        self.builder = builder
        self.make_run = make_run

    async def run(self, step: RunTaskStep, state: Any, it: list[int]) -> dict[str, Any]:
        ctx = self.builder.ctx
        failed = (state.get("attempts") or {}).get(step.id) or {}
        retrying = failed.get("route") == "retry"
        started = failed["started"] if retrying else now_text()
        tries = failed["tries"] + 1 if retrying else 1
        info = get_runtime().execution_info
        assert info is not None  # set for every node LangGraph runs
        caller = get_config()["configurable"]["thread_id"]
        # One called run per pass of the step: the same across its pauses and tries, a new one
        # when the caller is retried from an earlier step.
        thread = str(failed.get("thread") or "") if retrying else ""
        thread = thread or f"{caller}~{step.id}~{info.task_id}"
        await self.builder.emit(StepRecord(step.id, "running", started, iteration=it,
                                           attempts=tries))  # fmt: skip
        try:
            if ctx.tasks is None:
                raise StepFailed("Running another task can't happen here")
            task = ctx.tasks.load(step.id, step.task)
            results = await self._called(step, task, values=state["values"], it=it, thread=thread)
        except GraphBubbleUp:
            raise
        except Exception as exc:  # noqa: BLE001 -- recorded, then recovered from or raised
            recovered = await self.builder.recover(step, state, it, started, tries, exc)
            way = recovered.get("attempts", {}).get(step.id, {})
            if way.get("route") == "retry":
                way["thread"] = thread
            return recovered
        await self.builder.emit(StepRecord(step.id, "done", started, now_text(), iteration=it,
                                           output=preview(results), attempts=tries))  # fmt: skip
        made = {step.save_as: results} if step.save_as else {}
        return {"values": made, "attempts": {step.id: {"route": "ok"}}}

    async def _called(
        self, step: RunTaskStep, task: CalledTask, *, values: dict[str, Any], it: list[int],
        thread: str,
    ) -> dict[str, Any]:  # fmt: skip
        """Take the called run as far as it goes: to its end, or to a pause passed up."""
        ctx = self.builder.ctx
        assert ctx.tasks is not None

        async def on_step(record: StepRecord) -> None:
            await self.builder.emit(replace(record, step_id=f"{step.id}/{record.step_id}",
                                            iteration=[*it, *record.iteration]))  # fmt: skip

        inner = replace(ctx, approval_mode=task.approval_mode,
                        tasks=ctx.tasks.below(step.id, task.task_id))  # fmt: skip
        run = self.make_run(task.workflow, inner, self.builder.checkpointer, thread, on_step)
        outcome = await _alone(run.settled())
        if outcome is None:
            given = {name: render_value(text, values) for name, text in step.inputs.items()}
            outcome = await _alone(run.start(given, task.memory))
        elif outcome.status == "failed":
            outcome = await _alone(run.resume())
        while outcome.status == "waiting":
            request = outcome.request or {}
            key = f"{thread}@{await _alone(run.checkpoint_id())}"
            inner_id = f"{step.id}/{request.get('step_id')}"
            answer = interrupt({**request, "step_id": inner_id, "call_id": key,
                                "task": task.name})  # fmt: skip
            if not isinstance(answer, dict) or answer.get("call_id") != key:
                continue  # an answer to an earlier pause, replayed
            if answer.get("woke"):
                outcome = await _alone(run.wake())
            else:
                note = str(answer.get("note") or "")
                approved = answer.get("approved") is True
                outcome = await _alone(run.answer(approved, note, answer.get("values")))
        if outcome.status == "failed":
            raise StepFailed(f"“{task.name}” stopped: {outcome.error}",
                             declined=outcome.declined)  # fmt: skip
        ctx.tasks.keep(task.task_id, outcome.remembered)
        results: dict[str, Any] = outcome.results
        return results
