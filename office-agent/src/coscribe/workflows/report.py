"""A workflow run's report (decision 0030): what was done and what wasn't, what an agent decided
on its own, which steps that can't be taken back ran, and what the agents used -- read from the
run's step records, so a person trusts a run by its result, not by watching every step."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..workflow_spec import LoopStep, Workflow, walk


def _seconds(started: str | None, finished: str | None) -> float | None:
    if not started or not finished:
        return None
    try:
        return round(
            (datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds(), 1
        )
    except ValueError:
        return None


def run_report(
    workflow: Workflow,
    records: list[dict[str, Any]],
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    """{"autonomy", "loops": [{"step_id", "title", "done", "total"}], "not_done": [{"step_id",
    "title", "iteration", "status", "error"}], "assumed": [{"step_id", "title", "iteration",
    "values"}], "irreversible": [{"step_id", "title", "iteration"}], "tool_calls", "tokens",
    "seconds"}. A step that was removed from the workflow after the run keeps its id as title."""
    steps = {placed.step.id: placed.step for placed in walk(workflow.steps)}

    def title(step_id: str) -> str:
        step = steps.get(step_id)
        return step.title if step is not None else step_id

    loops, not_done, assumed, irreversible = [], [], [], []
    tool_calls = tokens = 0
    for record in records:
        step_id = str(record.get("step_id") or "")
        step = steps.get(step_id)
        status = record.get("status")
        where = {
            "step_id": step_id,
            "title": title(step_id),
            "iteration": record.get("iteration") or [],
        }
        output = record.get("output")
        if isinstance(step, LoopStep) and isinstance(output, dict) and "total" in output:
            loops.append({"step_id": step_id, "title": title(step_id),
                          "done": output.get("done", 0), "total": output["total"]})  # fmt: skip
        if status in ("failed", "waiting"):
            not_done.append({**where, "status": status, "error": record.get("error")})
        # Marked steps are decision 0029's; a workflow from before it has none.
        if status == "done" and getattr(step, "irreversible", False):
            irreversible.append(where)
        agent = record.get("agent")
        if isinstance(agent, dict):
            tool_calls += int(agent.get("tool_calls") or 0)
            tokens += int(agent.get("tokens") or 0)
            if agent.get("assumed"):
                assumed.append({**where, "values": list(agent["assumed"])})
    return {
        "autonomy": workflow.effective_autonomy(),
        "loops": loops,
        "not_done": not_done,
        "assumed": assumed,
        "irreversible": irreversible,
        "tool_calls": tool_calls,
        "tokens": tokens,
        "seconds": _seconds(started_at, finished_at),
    }
