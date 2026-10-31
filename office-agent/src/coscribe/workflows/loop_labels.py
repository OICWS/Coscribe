"""A workflow loop's pieces the engine shows or sizes by: short labels for its items in the
run view, its progress, and how many graph steps a run can take."""

from __future__ import annotations

import json
from typing import Any

from ..workflow_spec import BranchStep, LoopStep, Step

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
        if isinstance(step, BranchStep):
            total += 1 + max(supersteps(step.then), supersteps(step.otherwise))
        elif isinstance(step, LoopStep):
            total += 2 + step.max_items * (supersteps(step.steps) + 2)
        else:
            total += 1
    return total


def loop_progress(loop: dict[str, Any]) -> dict[str, Any]:
    return {"done": loop["index"], "total": len(loop["items"]), "items": loop["labels"]}
