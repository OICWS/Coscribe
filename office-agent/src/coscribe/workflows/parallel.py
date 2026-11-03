"""A step that runs its lanes at the same time (decision 0036). Each lane runs as a run of its
own, like a called task (decision 0035): on its own checkpoint thread in the caller's store,
starting from the values the caller had, its records the caller's under their own ids. The
step waits for every lane to end; then their pauses go up one at a time, keyed by where the
lane stopped, since LangGraph replays every earlier answer when the step runs again. A lane
that fails lets the others end, then the step fails; a retry goes on in the lanes that failed
and leaves the ones that finished as they are. Lanes that use the browser take turns, since
there is one."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from langgraph.config import get_config
from langgraph.errors import GraphBubbleUp
from langgraph.runtime import get_runtime
from langgraph.types import interrupt

from ..workflow_spec import (
    AgentStep,
    Lane,
    ParallelStep,
    RunTaskStep,
    Step,
    ToolStep,
    Workflow,
    step_output,
    walk,
)
from .run_task import _alone, _Builder
from .step_work import StepFailed, StepRecord, now_text, preview


def _lane_workflow(caller: Workflow, lane: Lane) -> Workflow:
    # Not validated again: a lane reads what came before the step, which it doesn't hold.
    return caller.model_copy(update={"steps": lane.steps, "after_failure": []})


def _may_browse(step: Step) -> bool:
    if isinstance(step, ToolStep):
        return step.tool.startswith("browser_")
    if isinstance(step, AgentStep):
        browses = step.sites or any(t.startswith("browser_") for t in step.tools)
        return bool(browses) or step.autonomy != "bounded"
    # What a called task does is known only once it is loaded.
    return isinstance(step, RunTaskStep)


def _uses_browser(lane: Lane) -> bool:
    return any(_may_browse(p.step) for p in walk(lane.steps))


def _made(lane: Lane, values: dict[str, Any]) -> dict[str, Any]:
    """What a lane saved, for the steps after the parallel step."""
    names = {name for p in walk(lane.steps) if (name := step_output(p.step))}
    return {name: values[name] for name in names if name in values}


def _failed(step: ParallelStep, outcomes: list[Any]) -> None:
    """Fail the step for its lanes that failed; one still waiting is asked again on a retry."""
    lanes = zip(step.lanes, outcomes, strict=True)
    failed = [(lane.label, o) for lane, o in lanes if o.status == "failed"]
    if failed:
        errors = "; ".join(f"{label}: {outcome.error}" for label, outcome in failed)
        raise StepFailed(errors, declined=any(o.declined for _label, o in failed))


class ParallelSteps:
    """Runs the parallel steps of the graph builder that owns them."""

    def __init__(self, builder: _Builder, make_run: Callable[..., Any], caller: Workflow) -> None:
        self.builder = builder
        self.make_run = make_run
        self.caller = caller

    async def run(self, step: ParallelStep, state: Any, it: list[int]) -> dict[str, Any]:
        failed = (state.get("attempts") or {}).get(step.id) or {}
        retrying = failed.get("route") == "retry"
        started = failed["started"] if retrying else now_text()
        tries = failed["tries"] + 1 if retrying else 1
        info = get_runtime().execution_info
        assert info is not None  # set for every node LangGraph runs
        caller = get_config()["configurable"]["thread_id"]
        # One set of lane runs per pass of the step, kept across its pauses and tries.
        base = str(failed.get("thread") or "") if retrying else ""
        base = base or f"{caller}~{step.id}~{info.task_id}"
        await self.builder.emit(StepRecord(step.id, "running", started, iteration=it,
                                           attempts=tries))  # fmt: skip
        try:
            made, remembered = await self._lanes(step, state["values"], it, base)
        except GraphBubbleUp:
            raise
        except (StepFailed, ValueError, KeyError, OSError) as exc:
            recovered = await self.builder.recover(step, state, it, started, tries, exc)
            way = recovered.get("attempts", {}).get(step.id, {})
            if way.get("route") == "retry":
                way["thread"] = base
            return recovered
        done = {"lanes": len(step.lanes), "made": sorted(made)}
        await self.builder.emit(StepRecord(step.id, "done", started, now_text(), iteration=it,
                                           output=preview(done), attempts=tries))  # fmt: skip
        return {"values": made, "remembered": remembered, "attempts": {step.id: {"route": "ok"}}}

    async def _lanes(
        self, step: ParallelStep, values: dict[str, Any], it: list[int], base: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        ctx = self.builder.ctx
        browser = asyncio.Lock()
        lane_ids = {p.step.id for lane in step.lanes for p in walk(lane.steps)}

        async def on_step(record: StepRecord) -> None:
            await self.builder.emit(replace(record, iteration=[*it, *record.iteration]))

        runs = [
            self.make_run(_lane_workflow(self.caller, lane), ctx, self.builder.checkpointer,
                          f"{base}~{index}", on_step)
            for index, lane in enumerate(step.lanes)
        ]  # fmt: skip

        async def settle(index: int) -> Any:
            run, lane = runs[index], step.lanes[index]
            async with browser if _uses_browser(lane) else contextlib.nullcontext():
                outcome = await run.settled()
                if outcome is None:
                    return await run.start_from(dict(values))
                if outcome.status != "failed":
                    return outcome
                # As a retry of a step at the top: a person said no there is asked again.
                stopped = str(outcome.step_id or "")
                again = stopped in lane_ids and "/" not in stopped
                return await (run.retry_from(stopped) if again else run.resume())

        outcomes = list(await _alone(asyncio.gather(*(settle(i) for i in range(len(runs))))))
        _failed(step, outcomes)
        for index, run in enumerate(runs):
            outcomes[index] = await self._answered(run, outcomes[index], f"{base}~{index}")
        _failed(step, outcomes)
        made: dict[str, Any] = {}
        remembered: dict[str, Any] = {}
        for lane, outcome in zip(step.lanes, outcomes, strict=True):
            made |= _made(lane, outcome.values)
            remembered |= outcome.remembered
        return made, remembered

    async def _answered(self, run: Any, outcome: Any, thread: str) -> Any:
        """The lane taken on past each of its pauses, each answered by a person in turn."""
        while outcome.status == "waiting":
            request = outcome.request or {}
            key = f"{thread}@{await _alone(run.checkpoint_id())}"
            answer = interrupt({**request, "call_id": key})
            if not isinstance(answer, dict) or answer.get("call_id") != key:
                continue  # an answer to an earlier pause, replayed
            if answer.get("woke"):
                outcome = await _alone(run.wake())
            else:
                note = str(answer.get("note") or "")
                approved = answer.get("approved") is True
                outcome = await _alone(run.answer(approved, note, answer.get("values")))
        return outcome
