"""Short labels for the items of a workflow loop, shown in the run view."""

from __future__ import annotations

import json
from typing import Any

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
