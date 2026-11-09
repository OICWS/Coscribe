"""Which way the run goes from a node: the route a failure there took (decision 0032), a branch's
arm, or a loop's next pass. Kept out of the engine, which is at its size limit."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..workflow_spec import BranchStep, ChoiceStep, LoopStep, Step, choose_arm

Router = Callable[[Mapping[str, Any]], str]


def routed(step: Step, router: Router | None) -> Router:
    def route(state: Mapping[str, Any]) -> str:
        taken = ((state.get("attempts") or {}).get(step.id) or {}).get("route", "ok")
        if taken != "ok":
            return str(taken)
        return router(state) if router is not None else "ok"

    return route


def arm_router(step: BranchStep | ChoiceStep) -> Router:
    # Re-evaluating is safe: the branch node already evaluated the same
    # values without error, and nothing has changed them since.
    return lambda state: choose_arm(step, state["values"])[0]


def more(loop: dict[str, Any]) -> bool:
    return loop["index"] < len(loop["items"]) and not loop.get("stopped_early")


def loop_router(step: LoopStep) -> Router:
    return lambda state: "body" if more(state["loops"][step.id]) else "done"
