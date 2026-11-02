"""A workflow loop's pieces the engine shows or sizes by: short labels for its items in the
run view, its progress, and how many graph steps a run can take."""

from __future__ import annotations

import json
from typing import Any

from ..workflow_spec import (
    AskStep,
    BranchStep,
    ChoiceStep,
    LoopStep,
    Step,
    WaitStep,
    child_lists,
    failure_policy,
)

_ITEM_LABEL_CHARS = 60
_LABEL_KEYS = ("name", "title", "path", "file", "id", "text")


def _short(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _ITEM_LABEL_CHARS else text[: _ITEM_LABEL_CHARS - 1] + "…"


def item_labels(items: list[Any]) -> list[str]:
    """A few words naming each of a loop's items, for picking a pass in the
    run view -- the items themselves can be large. For records, the first
    field that tells them apart (search hits all share their `path`)."""
    records = [item for item in items if isinstance(item, dict)]
    key = None
    if records and len(records) == len(items):
        present = [k for k in _LABEL_KEYS if all(isinstance(r.get(k), str) for r in records)]
        key = next((k for k in present if len({r[k] for r in records}) == len(records)), None)
        key = key or next(iter(present), None)
    labels = []
    for item in items:
        if key is not None:
            labels.append(_short(item[key]))
        elif isinstance(item, str):
            labels.append(_short(item))
        else:
            labels.append(_short(json.dumps(item, ensure_ascii=False, default=str)))
    return labels


def supersteps(steps: list[Step]) -> int:
    """The most graph steps `steps` can take -- LangGraph stops a run that
    goes past its recursion limit, and a loop legitimately goes round."""
    total = 0
    for step in steps:
        if isinstance(step, (BranchStep, ChoiceStep)):
            total += 1 + max(supersteps(steps) for _arm, steps in child_lists(step))
        elif isinstance(step, LoopStep):
            total += 2 + step.max_items * (supersteps(step.steps) + 2)
        elif isinstance(step, (AskStep, WaitStep)):
            # It settles its deadline, then pauses: each resume that isn't its end goes round once
            # more, in a run of its own (decision 0033).
            total += 3
        else:
            # Each try is a graph step, and the steps in its place follow the last (decision 0032).
            policy = failure_policy(step)
            total += 1 + (policy.retries + supersteps(policy.steps) if policy else 0)
    return total


def loop_progress(loop: dict[str, Any]) -> dict[str, Any]:
    """`done` counts the items gone through, the skipped ones (decision 0032) among them."""
    progress = {"done": loop["index"], "total": len(loop["items"]), "items": loop["labels"]}
    if loop.get("skipped"):
        progress["skipped"] = loop["skipped"]
    # Its `until` held after the last pass, so the rest of the items were left on purpose.
    return {**progress, "stopped_early": True} if loop.get("stopped_early") else progress
