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
import logging
from collections.abc import Awaitable, Callable, Hashable
from dataclasses import dataclass, field, replace
from typing import Annotated, Any, Literal, TypedDict, cast

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import get_runtime
from langgraph.types import Command, interrupt

from ..needs_permission import NeedsPermission
from ..workflow_spec import (
    FAILURE,
    AgentStep,
    ApprovalStep,
    AskStep,
    BranchStep,
    CheckStep,
    ChoiceStep,
    LLMStep,
    LoopStep,
    ParallelStep,
    Placed,
    RememberStep,
    RunTaskStep,
    ScriptStep,
    Step,
    ToolStep,
    WaitStep,
    Workflow,
    child_lists,
    choose_arm,
    conditions_hold,
    failure_policy,
    resolve,
    step_output,
    walk,
)
from .agent_step import AgentCall, CallGuard, answer_of, run_agent_step
from .healing import carried, heal_guard, healed, stand_in
from .loop_labels import item_labels as _item_labels
from .loop_labels import loop_progress as _loop_progress
from .loop_labels import supersteps as _supersteps
from .parallel import ParallelSteps
from .pause_steps import PAUSED, Pauses
from .permissions import untrusted_agent_steps
from .preflight import NO_STEPS as _NO_STEPS
from .preflight import UNAVAILABLE_TOOLS as UNAVAILABLE_TOOLS
from .preflight import WorkflowNotRunnable as WorkflowNotRunnable
from .preflight import preflight, starting_values
from .remember_steps import ENDED, check_or_end, remember
from .run_task import TaskSteps, given_results
from .step_work import StepContext as StepContext
from .step_work import StepFailed as StepFailed
from .step_work import StepRecord as StepRecord
from .step_work import StepStatus, checks_of, preview, run_check, run_llm, run_script, run_tool
from .step_work import now_text as _now

logger = logging.getLogger(__name__)

RunOutcomeStatus = Literal["completed", "failed", "waiting"]


@dataclass
class RunOutcome:
    status: RunOutcomeStatus
    step_id: str | None = None
    error: str | None = None
    # For "waiting": what the approval step asks.
    request: dict[str, Any] | None = None
    values: dict[str, Any] = field(default_factory=dict)
    # For "completed" (decision 0034): what its remember steps keep, and whether a check ended
    # it with nothing to do.
    remembered: dict[str, Any] = field(default_factory=dict)
    ended: bool = False
    # For "completed", what it gives a task that ran it (decision 0035); for "failed", whether a
    # person said no.
    results: dict[str, Any] = field(default_factory=dict)
    declined: bool = False


OnStep = Callable[[StepRecord], Awaitable[None] | None]


def _merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {**left, **right}


class _State(TypedDict):
    values: Annotated[dict[str, Any], _merge]
    # Per loop id: {"index", "items", "results", "started_at"} of its
    # current pass.
    loops: Annotated[dict[str, Any], _merge]
    # Per step id: how it was last healed in this run (decision 0030), for its later passes.
    healed: Annotated[dict[str, Any], _merge]
    # Per memory name: what this run's remember steps keep (decision 0034).
    remembered: Annotated[dict[str, Any], _merge]
    # Per step id, in its current pass: {"route", "tries", "started"} -- where the run goes from
    # it and how many of its tries have failed (decision 0032). Each try is its own graph step,
    # so a pause during one resumes that try, not the first.
    attempts: Annotated[dict[str, Any], _merge]


def _node_name(step: Step) -> str:
    # A node can't share a name with a state key ("values").
    return f"step__{step.id}"


class _GraphBuilder:
    def __init__(
        self, workflow: Workflow, ctx: StepContext, on_step: OnStep, *, unattended: bool = False
    ) -> None:
        self.workflow = workflow
        self.ctx = ctx
        self.on_step = on_step
        # The steps after a failed run (decision 0032): no one is there to answer them, so an
        # agent's question is answered no instead of pausing the run.
        self.unattended = unattended
        self.placed = {p.step.id: p for p in walk(workflow.steps)}
        self.read_only = set(untrusted_agent_steps(workflow, ctx.outside_tools))
        self.graph = StateGraph(_State)
        self.pauses = Pauses(self)
        self.tasks = TaskSteps(self, WorkflowRun)
        self.parallel = ParallelSteps(self, WorkflowRun, workflow)
        self.checkpointer: Any = None

    async def emit(self, record: StepRecord) -> None:
        result = self.on_step(record)
        if inspect.isawaitable(result):
            await result

    def iteration(self, state: _State, step: Step) -> list[int]:
        loops = state.get("loops") or {}
        return [loops[loop_id]["index"] for loop_id in self.placed[step.id].loops]

    async def fail(
        self,
        step: Step,
        it: list[int],
        started: str,
        exc: Exception,
        attempts: int = 1,
        recovered: Literal["skipped", "fallback", "item_skipped"] | None = None,
        output: Any = None,
    ) -> StepFailed:
        if isinstance(exc, StepFailed):
            failure = exc
        else:
            failure = StepFailed(str(exc) or type(exc).__name__)
        failure.step_id = step.id
        await self.emit(
            StepRecord(step.id, "failed", started, _now(), output=output, error=str(failure),
                       checks=failure.checks, iteration=it, attempts=attempts,
                       recovered=recovered)
        )  # fmt: skip
        return failure

    def skipping_loop(self, step: Step) -> str | None:
        """The innermost loop around `step` that skips an item a step fails on, if any."""
        around = self.placed[step.id].loops
        loops = {p.step.id: p.step for p in self.placed.values() if p.step.id in around}
        skipping = [i for i in around if cast(LoopStep, loops[i]).on_item_failure == "skip"]
        return skipping[-1] if skipping else None

    def routes(self, step: Step, following: str) -> dict[str, str]:
        """Where the run goes from `step` other than on success (decision 0032); empty when a
        failure there stops the run."""
        routes: dict[str, str] = {}
        policy = failure_policy(step)
        if policy is not None:
            in_place = policy.steps
            routes |= {"retry": _node_name(step), "skip": following,
                       "steps": _node_name(in_place[0]) if in_place else following}  # fmt: skip
        if isinstance(step, (AskStep, WaitStep)):
            routes[PAUSED] = _node_name(step)
        if isinstance(step, CheckStep) and step.otherwise == ENDED:
            routes[ENDED] = END
        # A person's no stops the run, wherever it is.
        loop = None if isinstance(step, (ApprovalStep, AskStep)) else self.skipping_loop(step)
        if loop is not None:
            routes["skip_item"] = f"next__{loop}"
        return routes

    async def recover(
        self, step: Step, state: _State, it: list[int], started: str, tries: int, exc: Exception,
        output: Any = None,
    ) -> dict[str, Any]:  # fmt: skip
        """After a failed try: try again, skip the step, run the steps in its place, skip the
        loop's item, or stop the run (decision 0032)."""
        policy = failure_policy(step)
        error = str(exc) or type(exc).__name__
        again = not (isinstance(exc, StepFailed) and exc.declined)
        if policy is not None and tries <= policy.retries and again:
            await self.emit(StepRecord(step.id, "running", started, iteration=it, attempts=tries,
                                       error=f"Try {tries} didn't work: {error}"))  # fmt: skip
            await asyncio.sleep(min(policy.wait_seconds, self.ctx.max_retry_wait))
            return {"attempts": {step.id: {"route": "retry", "tries": tries, "started": started}}}
        then = policy.then if policy is not None else "stop"
        if then != "stop":
            how: Literal["skipped", "fallback"] = "skipped" if then == "skip" else "fallback"
            await self.fail(step, it, started, exc, tries, how)
            made = {FAILURE: {"step": step.title, "message": error}} if then == "steps" else {}
            return {"values": made, "attempts": {step.id: {"route": then}}}
        loop = self.skipping_loop(step)
        if loop is None:
            failure = await self.fail(step, it, started, exc, tries, output=output)
            if failure is exc:
                raise failure
            raise failure from exc
        await self.fail(step, it, started, exc, tries, "item_skipped", output)
        return await self.skip_item(step, loop, state, error)

    async def skip_item(
        self, step: Step, loop_id: str, state: _State, error: str
    ) -> dict[str, Any]:
        """Leave the item of `loop_id` that `step` failed on, and the loops inside its pass where
        they stopped, and go on with its next item."""
        around = self.placed[step.id].loops
        depth = around.index(loop_id)
        loops = state["loops"]
        it = [loops[i]["index"] for i in around]
        for inner_depth in range(depth + 1, len(around)):
            inner = loops[around[inner_depth]]
            await self.emit(
                StepRecord(around[inner_depth], "failed", inner["started_at"], _now(),
                           output=_loop_progress(inner), iteration=it[:inner_depth],
                           error=f"Stopped at item {inner['index'] + 1}: {error}",
                           recovered="item_skipped")
            )  # fmt: skip
        loop = loops[loop_id]
        index = loop["index"]
        skipped = [*loop.get("skipped", []), {"index": index, "label": loop["labels"][index],
                                               "error": error}]  # fmt: skip
        loop = {**loop, "index": index + 1, "skipped": skipped}
        await self.emit(StepRecord(loop_id, "running", loop["started_at"],
                                   output=_loop_progress(loop), iteration=it[:depth]))  # fmt: skip
        return {"loops": {loop_id: loop}, "attempts": {step.id: {"route": "skip_item"}}}

    def make_node(self, step: Step) -> Callable[[_State], Awaitable[dict[str, Any]]]:
        async def run(state: _State) -> dict[str, Any]:
            values = state["values"]
            it = self.iteration(state, step)
            if isinstance(step, ApprovalStep):
                return await self.pauses.approval(step, values, it)
            if isinstance(step, RememberStep):
                return await remember(self, step, values, it)
            if isinstance(step, RunTaskStep):
                return await self.tasks.run(step, state, it)
            if isinstance(step, ParallelStep):
                return await self.parallel.run(step, state, it)
            if isinstance(step, CheckStep) and step.otherwise == ENDED:
                return await check_or_end(self, step, values, it)
            if isinstance(step, (AskStep, WaitStep)):
                held = (state.get("attempts") or {}).get(step.id) or {}
                if held.get("route") != PAUSED:
                    return await self.pauses.settle(step, values, it)
                if isinstance(step, AskStep):
                    return await self.pauses.ask(step, values, held, it)
                return await self.pauses.wait(step, state, held, it)
            # Tries after the first carry on the step's record from when it started.
            failed = (state.get("attempts") or {}).get(step.id) or {}
            retrying = failed.get("route") == "retry"
            started = failed["started"] if retrying else _now()
            attempt = failed["tries"] + 1 if retrying else 1
            policy = failure_policy(step)
            last = policy is None or attempt > policy.retries
            await self.emit(StepRecord(step.id, "running", started_at=started, iteration=it,
                                       attempts=attempt))  # fmt: skip
            try:
                earlier = (state.get("healed") or {}).get(step.id)
                output, checks, agent = await self._try(step, values, started, it, earlier, last)
            except GraphBubbleUp:
                raise
            except Exception as exc:  # noqa: BLE001 -- recorded, then recovered from or raised
                return await self.recover(step, state, it, started, attempt, exc)
            await self.emit(
                StepRecord(step.id, "done", started, _now(), output=preview(output),
                           checks=checks, iteration=it, agent=agent, attempts=attempt)
            )  # fmt: skip
            save_as = None if isinstance(step, BranchStep) else step_output(step)
            heal = {"healed": {step.id: agent["healed"]}} if agent and "healed" in agent else {}
            return {"values": {save_as: output} if save_as else {}, **heal,
                    "attempts": {step.id: {"route": "ok"}}}  # fmt: skip

        return run

    async def _try(
        self, step: Step, values: dict[str, Any], started: str, it: list[int], earlier: Any,
        last: bool = True,
    ) -> tuple[Any, list[dict[str, Any]] | None, dict[str, Any] | None]:  # fmt: skip
        """A step's attempt, asking for what it needs; a failed browser step is healed when the
        task's autonomy allows it (decision 0030), and a later pass first tries what healed it.
        On resume after a pause in healing the step runs again from its start, and a step that
        still fails finds its agent where it was. Only its `last` try is healed: the ones
        before it are for a site that didn't answer, which an agent can't fix."""
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
            agent_step = stand_in(self.workflow, step, values, error, earlier) if last else None
            if agent_step is None or self.ctx.run_agent is None:
                raise
            try:
                guard = heal_guard(self.workflow, step, values)
                result, agent = await self._agent(agent_step, values, started, it, guard)
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
            return await run_tool(step, values, self.ctx), None, None
        if isinstance(step, ScriptStep):
            return await run_script(step, values, self.ctx), None, None
        if isinstance(step, LLMStep):
            return await run_llm(step, values, self.ctx), None, None
        if isinstance(step, AgentStep):
            output, agent = await self._agent(step, values, started, it)
            return output, None, agent
        if isinstance(step, CheckStep):
            return None, run_check(step, values), None
        if isinstance(step, (BranchStep, ChoiceStep)):
            arm, checked = choose_arm(step, values)
            return {"arm": arm}, checks_of(checked), None
        return None, None, None

    async def _agent(
        self, step: AgentStep, values: dict[str, Any], started: str, it: list[int],
        guard: CallGuard | None = None,
    ) -> tuple[Any, dict[str, Any]]:  # fmt: skip
        async def ask(call: AgentCall) -> dict[str, Any]:
            if self.unattended:
                note = "No one is there to answer: this step runs after the run failed."
                return {"approved": False, "note": note, "call_id": call.call_id}
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
            guard=guard,
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
            raise StepFailed(f"Not allowed: {need.message}", step_id=step.id, declined=True)
        await self.emit(StepRecord(step.id, "running", started_at=started, iteration=it))

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
                return await self.recover(step, state, it, started, 1, exc)
            loop = {
                "index": 0,
                "items": items,
                "labels": _item_labels(items),
                "results": [],
                "skipped": [],
                "started_at": started,
            }
            await self.emit(
                StepRecord(step.id, "running", started, output=_loop_progress(loop), iteration=it)
            )
            return {"loops": {step.id: loop}, "attempts": {step.id: {"route": "ok"}}}

        return run

    def loop_next(self, step: LoopStep) -> Callable[[_State], Awaitable[dict[str, Any]]]:
        async def run(state: _State) -> dict[str, Any]:
            loop = state["loops"][step.id]
            if _more(loop):
                return {"values": {step.item: loop["items"][loop["index"]]},
                        "attempts": {step.id: {"route": "ok"}}}  # fmt: skip
            skipped = loop.get("skipped") or []
            if skipped and len(skipped) == len(loop["items"]):
                it = self.iteration(state, step)
                failure = StepFailed(f"Every item failed. The last: {skipped[-1]['error']}")
                progress = _loop_progress(loop)
                return await self.recover(step, state, it, loop["started_at"], 1, failure, progress)
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
            made = {step.save_as: loop["results"]} if step.save_as else {}
            return {"values": made, "attempts": {step.id: {"route": "ok"}}}

        return run

    def loop_collect(self, step: LoopStep) -> Callable[[_State], Awaitable[dict[str, Any]]]:
        async def run(state: _State) -> dict[str, Any]:
            loop = state["loops"][step.id]
            it = self.iteration(state, step)
            try:
                value = resolve(step.collect, state["values"]) if step.collect else None
                stop = step.until and conditions_hold(step.until, step.match, state["values"])[0]
            except Exception as exc:  # noqa: BLE001 -- recorded like any step's failure
                failure = await self.fail(step, it, loop["started_at"], exc)
                if failure is exc:
                    raise
                raise failure from exc
            loop = {**loop, "index": loop["index"] + 1, "results": [*loop["results"], value]}
            loop = {**loop, "stopped_early": True} if stop else loop
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
            if isinstance(step, (BranchStep, ChoiceStep)):
                arms = child_lists(step)
                self.graph.add_node(node, cast(Any, self.make_node(step)))
                paths = {arm: _node_name(path[0]) if path else following for arm, path in arms}
                self.edges(node, step, following, _arm_router(step), paths)
                for _arm, path in arms:
                    self.wire(path, following)
            elif isinstance(step, LoopStep):
                next_node, collect_node = f"next__{step.id}", f"collect__{step.id}"
                self.graph.add_node(node, cast(Any, self.loop_start(step)))
                self.graph.add_node(next_node, cast(Any, self.loop_next(step)))
                self.graph.add_node(collect_node, cast(Any, self.loop_collect(step)))
                self.edges(node, step, next_node)
                body = _node_name(step.steps[0]) if step.steps else collect_node
                self.edges(next_node, step, following, _loop_router(step),
                           {"body": body, "done": following})  # fmt: skip
                self.wire(step.steps, collect_node)
                self.graph.add_edge(collect_node, next_node)
            else:
                self.graph.add_node(node, cast(Any, self.make_node(step)))
                self.edges(node, step, following)
                policy = failure_policy(step)
                if policy is not None and policy.then == "steps":
                    self.wire(policy.steps, following)

    def edges(
        self,
        node: str,
        step: Step,
        following: str,
        router: Callable[[_State], str] | None = None,
        targets: dict[str, str] | None = None,
    ) -> None:
        """`node`'s ways on: to `targets` by `router` when it worked (to `following` without
        one), and the routes a failure there takes (decision 0032)."""
        routes = self.routes(step, following)
        if router is None and not routes:
            self.graph.add_edge(node, following)
            return
        ways = [*(targets or {"ok": following}).items(), *routes.items()]
        destinations: dict[Hashable, str] = {way: target for way, target in ways}
        self.graph.add_conditional_edges(node, _routed(step, router), destinations)

    def build(self, checkpointer: Any) -> Any:
        self.checkpointer = checkpointer
        self.wire(self.workflow.steps, END)
        self.graph.add_edge(START, _node_name(self.workflow.steps[0]))
        return self.graph.compile(checkpointer=checkpointer)


def build_graph(workflow: Workflow, ctx: StepContext, on_step: OnStep, checkpointer: Any) -> Any:
    return _GraphBuilder(workflow, ctx, on_step).build(checkpointer)


def _routed(step: Step, router: Callable[[_State], str] | None) -> Callable[[_State], str]:
    def route(state: _State) -> str:
        taken = ((state.get("attempts") or {}).get(step.id) or {}).get("route", "ok")
        if taken != "ok":
            return str(taken)
        return router(state) if router is not None else "ok"

    return route


def _arm_router(step: BranchStep | ChoiceStep) -> Callable[[_State], str]:
    # Re-evaluating is safe: the branch node already evaluated the same
    # values without error, and nothing has changed them since.
    return lambda state: choose_arm(step, state["values"])[0]


def _more(loop: dict[str, Any]) -> bool:
    return loop["index"] < len(loop["items"]) and not loop.get("stopped_early")


def _loop_router(step: LoopStep) -> Callable[[_State], str]:
    return lambda state: "body" if _more(state["loops"][step.id]) else "done"


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

    async def start(
        self, inputs: dict[str, Any], memory: dict[str, Any] | None = None
    ) -> RunOutcome:
        preflight(self.workflow, self.ctx)
        values = starting_values(self.workflow, inputs, memory)
        return await self._drive({"values": values, "loops": {}, "attempts": {}})

    async def start_from(self, values: dict[str, Any]) -> RunOutcome:
        """A parallel step's lane: from the values the run had when the step began."""
        preflight(self.workflow, self.ctx)
        return await self._drive({"values": values, "loops": {}, "attempts": {}})

    async def resume(self) -> RunOutcome:
        """Carry on after a crash or a failed step's cause being fixed. A
        declined approval stays declined here -- LangGraph replays the
        recorded answer -- so asking again is retry_from() that step."""
        return await self._drive(None)

    async def answer(
        self, approved: bool, note: str = "", values: dict[str, Any] | None = None
    ) -> RunOutcome:
        answer = {"approved": approved, "note": note, "values": values}
        return await self._drive(Command(resume={**answer, "call_id": await self._call_id()}))

    async def wake(self) -> RunOutcome:
        """Go on with a run paused at a wait step whose time came or whose file appeared, or at
        an ask step no one answered in time (decision 0033)."""
        return await self._drive(Command(resume={"woke": True, "call_id": await self._call_id()}))

    async def _call_id(self) -> Any:
        """What the pause being answered names: an agent's call, or a called task's pause.
        Resuming replays earlier answers by position, and neither may take one for another."""
        state = await self._compiled.aget_state(self.config)
        asked = [i.value for t in state.tasks for i in t.interrupts if isinstance(i.value, dict)]
        return asked[0].get("call_id") if asked else None

    async def settled(self) -> RunOutcome | None:
        """Where this run stands, without taking it further: None when it never started;
        "failed" when it stopped part way, for resume() to go on with."""
        if self._graph is None:
            return None
        state = await self._graph.aget_state(self.config)
        if not state.values:
            return None
        # A step that failed on an answer still holds the pause it answered.
        if state.next and any(t.error or not t.interrupts for t in state.tasks):
            stopped = state.next[0].removeprefix("step__") if len(state.next) == 1 else None
            return RunOutcome("failed", step_id=stopped, values=state.values.get("values", {}))
        return await self._outcome(state)

    async def checkpoint_id(self) -> str:
        state = await self._compiled.aget_state(self.config)
        return str(state.config["configurable"]["checkpoint_id"])

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

    async def _after_failure(self, values: dict[str, Any], failure: StepFailed) -> None:
        """Run the steps for a failed run (decision 0032) with the run's inputs and what failed,
        unless a person said no: they know the run stopped. No one may be watching, so nothing
        in them waits for a person: what would ask fails instead. Their own failure is on their
        records and never hides the run's."""
        steps = self.workflow.after_failure
        if not steps or failure.declined:
            return
        placed = self._placed.get(failure.step_id or "")
        about = {"step": placed.step.title if placed else failure.step_id, "message": str(failure)}
        workflow = self.workflow.model_copy(update={"steps": steps, "after_failure": []})
        ctx = replace(self.ctx, ask_permission=False)
        graph = _GraphBuilder(workflow, ctx, self.on_step, unattended=True).build(InMemorySaver())
        config = {"configurable": {"thread_id": "after-failure"},
                  "recursion_limit": _supersteps(steps) + 10}  # fmt: skip
        try:
            await graph.ainvoke({"values": {**values, FAILURE: about}, "loops": {},
                                 "attempts": {}}, config)  # fmt: skip
        except StepFailed:
            pass
        except Exception:
            logger.warning("workflow: the steps after a failed run stopped", exc_info=True)

    def _loops_around(self, node: str) -> tuple[str, ...]:
        kind, _, step_id = node.partition("__")
        # A called task's step stops inside the step that runs it (decision 0035).
        placed = self._placed.get(step_id.split("/", 1)[0])
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
            values = state.values.get("values", {})
            await self._after_failure(values, exc)
            return RunOutcome("failed", step_id=exc.step_id, error=str(exc), values=values,
                              declined=exc.declined)  # fmt: skip
        return await self._outcome(await graph.aget_state(self.config))

    async def _outcome(self, state: Any) -> RunOutcome:
        values = state.values.get("values", {})
        for task in state.tasks:
            for pending in task.interrupts:
                request = pending.value if isinstance(pending.value, dict) else {}
                await self._mark_loops(f"step__{request.get('step_id')}", "waiting", None)
                return RunOutcome(
                    "waiting", step_id=request.get("step_id"), request=request, values=values
                )
        attempts = (state.values.get("attempts") or {}).values()
        return RunOutcome(
            "completed",
            values=values,
            ended=any(a.get("route") == ENDED for a in attempts),
            remembered=state.values.get("remembered") or {},
            results=given_results(self.workflow, values),
        )
