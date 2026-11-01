"""The revision a run's heals propose (decision 0030): a heal fixes the step for that run only,
so the next run would heal the same change again. A heal that named the saved arguments it
changed is a revision the person can keep with one click; the rest changed more than a step's
arguments and are left to a revision drafted in a conversation.

A fix replaces a saved argument only while it still holds the value the heal replaced, so a
task edited since the run is never overwritten with what an old run saw."""

from __future__ import annotations

import copy
from typing import Any

from ..workflow_spec import parse_workflow
from .report import run_report

# A branch's arms and a loop's body: where a step dict holds other steps.
_CHILD_LISTS = ("steps", "then", "otherwise")


def _find(steps: list[Any], step_id: str) -> dict[str, Any] | None:
    for step in steps:
        if not isinstance(step, dict):
            continue
        if step.get("id") == step_id:
            return step
        for key in _CHILD_LISTS:
            found = _find(step.get(key) or [], step_id)
            if found is not None:
                return found
    return None


def heal_fixes(workflow: dict[str, Any], healed: list[dict[str, Any]]) -> dict[str, Any]:
    """{"fixes": [{"step_id", "title", "name", "was", "now"}], "workflow": the saved workflow
    with every fix, or None when there is none, "left": [{"step_id", "title", "did"}]} from
    the run report's `healed` entries."""
    proposed: dict[tuple[str, str], set[str]] = {}
    replaced: dict[tuple[str, str], str] = {}
    titles: dict[str, str] = {}
    left: dict[str, dict[str, Any]] = {}
    for entry in healed:
        step_id = str(entry.get("step_id") or "")
        titles[step_id] = str(entry.get("title") or step_id)
        if entry.get("carried"):
            continue
        args, was = entry.get("args") or {}, entry.get("was") or {}
        if not args:
            left.setdefault(step_id, {"step_id": step_id, "title": titles[step_id],
                                      "did": str(entry.get("did") or "")})  # fmt: skip
        for name, now in args.items():
            if name in was:
                proposed.setdefault((step_id, name), set()).add(str(now))
                replaced[(step_id, name)] = str(was[name])
    revised = copy.deepcopy(workflow)
    fixes: list[dict[str, Any]] = []
    for (step_id, name), values in proposed.items():
        step = _find(revised.get("steps") or [], step_id)
        args = step.get("args") if step is not None and step.get("kind") == "tool" else None
        if len(values) > 1:
            # Healed differently on different items: no one value is the step's.
            did = f"{name} was healed to {len(values)} different values on different items."
            left.setdefault(step_id, {"step_id": step_id, "title": titles[step_id], "did": did})
        elif isinstance(args, dict) and args.get(name) == replaced[(step_id, name)]:
            (now,) = values
            args[name] = now
            fixes.append({"step_id": step_id, "title": titles[step_id], "name": name,
                          "was": replaced[(step_id, name)], "now": now})  # fmt: skip
    return {"fixes": fixes, "workflow": revised if fixes else None, "left": list(left.values())}


def heals_to_revise(
    workflow: dict[str, Any] | None, status: str, records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The heals of a finished run that a saved fix can't keep, as the run report lists them
    (what failed and what the agent did instead): a revision has to be drafted for them."""
    if workflow is None or status != "completed":
        return []
    healed = run_report(parse_workflow(workflow), records)["healed"]
    left = {item["step_id"] for item in heal_fixes(workflow, healed)["left"]}
    return [h for h in healed if h["step_id"] in left and not h.get("carried")]
