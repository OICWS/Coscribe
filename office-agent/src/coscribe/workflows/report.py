"""A workflow run's report (decision 0030): what was done and what wasn't, what an agent decided
on its own, which steps were healed while running (decision 0030), which steps that can't be
taken back ran, which failures didn't stop it (decision 0032), and what the agents used -- read
from the run's step records, so a person trusts a run by its result, not by watching every
step."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..workflow_spec import LoopStep, Workflow, walk
from .pause_steps import NO_ANSWER


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
    """{"autonomy", "loops": [{"step_id", "title", "done", "total", "skipped"}],
    "not_done": [{"step_id", "title", "iteration", "status", "error"}],
    "assumed": [{"step_id", "title", "iteration", "values"}],
    "unanswered": [{"step_id", "title", "iteration"}],
    "healed": [{"step_id", "title", "iteration", "error", "did"}],
    "irreversible": [{"step_id", "title", "iteration"}],
    "recovered": [{"step_id", "title", "iteration", "how", "error"}],
    "retried": [{"step_id", "title", "iteration", "attempts", "worked"}],
    "after_failure": [{"step_id", "title", "status", "error"}],
    "tool_calls", "tokens", "cached_tokens", "seconds"}. A loop's `done` counts the items that
    worked. A step that was removed from the workflow after the run keeps its id as title."""
    steps = {placed.step.id: placed.step for placed in walk(workflow.every_step())}
    after = {placed.step.id for placed in walk(workflow.after_failure)}

    def title(step_id: str) -> str:
        step = steps.get(step_id)
        return step.title if step is not None else step_id

    loops, not_done, assumed, healed, irreversible = [], [], [], [], []
    # Ask steps no one answered in time, which went on with their defaults (decision 0033).
    unanswered: list[dict[str, Any]] = []
    recovered: list[dict[str, Any]] = []
    retried: list[dict[str, Any]] = []
    after_failure: list[dict[str, Any]] = []
    tool_calls = tokens = cached = 0
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
            # The loop counts the items it went through; the report, the ones that worked.
            skipped = len(output.get("skipped") or [])
            done = output.get("done", 0) - skipped
            loops.append({"step_id": step_id, "title": title(step_id), "done": done,
                          "total": output["total"], "skipped": skipped})  # fmt: skip
        if record.get("recovered"):
            recovered.append({**where, "how": record["recovered"], "error": record.get("error")})
        elif step_id in after and status in ("done", "failed"):
            after_failure.append({**where, "status": status, "error": record.get("error")})
        elif status in ("failed", "waiting"):
            not_done.append({**where, "status": status, "error": record.get("error")})
        if int(record.get("attempts") or 1) > 1 and status in ("done", "failed"):
            retried.append({**where, "attempts": record["attempts"], "worked": status == "done"})
        # Marked steps are decision 0029's; a workflow from before it has none.
        if status == "done" and getattr(step, "irreversible", False):
            irreversible.append(where)
        if status == "done" and record.get("note") == NO_ANSWER:
            unanswered.append(where)
        agent = record.get("agent")
        if isinstance(agent, dict):
            tool_calls += int(agent.get("tool_calls") or 0)
            tokens += int(agent.get("tokens") or 0)
            cached += int(agent.get("cached_tokens") or 0)
            if agent.get("assumed"):
                assumed.append({**where, "values": list(agent["assumed"])})
            if isinstance(agent.get("healed"), dict):
                healed.append({**where, **agent["healed"]})
    return {
        "autonomy": workflow.effective_autonomy(),
        "loops": loops,
        "not_done": not_done,
        "assumed": assumed,
        "unanswered": unanswered,
        "healed": healed,
        "irreversible": irreversible,
        "recovered": recovered,
        "retried": retried,
        "after_failure": after_failure,
        "tool_calls": tool_calls,
        "tokens": tokens,
        "cached_tokens": cached,
        "seconds": _seconds(started_at, finished_at),
    }
