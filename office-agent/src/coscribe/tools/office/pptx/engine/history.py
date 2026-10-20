"""A deck's pages as they were after each build, for undo and redo in the Slides panel (design §9).

Every build records the folder's pages (and their comments) under `.history/`, one state per
build, labelled with who made it: "coscribe" for the model's builds, "you" for the panel's. A
state equal to the last one is not recorded again. Undo puts the previous state's pages back;
a new change after an undo drops the states that were undone.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

HISTORY = ".history"
_STATES = "states.json"
_KEEP = 50
_COMMENTS = "comments.json"


def record_state(folder: Path, pages: list[Path], by: str) -> None:
    root = folder / HISTORY
    log = read_log(folder)
    digest = _digest(folder, pages)
    states = log["states"][: log["at"] + 1]
    if states and states[-1]["digest"] == digest:
        return
    number = max((int(s["dir"]) for s in log["states"]), default=0) + 1
    target = root / str(number)
    target.mkdir(parents=True)
    for page in [*pages, folder / _COMMENTS]:
        if page.is_file():
            shutil.copy2(page, target / page.name)
    states.append({"dir": str(number), "by": by, "digest": digest})
    for dropped in [s for s in log["states"] if s not in states] + states[:-_KEEP]:
        shutil.rmtree(root / dropped["dir"], ignore_errors=True)
    states = states[-_KEEP:]
    _write_log(folder, {**log, "states": states, "at": len(states) - 1})


def read_log(folder: Path) -> dict[str, Any]:
    """The recorded states and which one the pages are now, and `told`, the state coscribe was
    last told the user's changes up to; empty when nothing was recorded or the record is not in
    the shape this module writes."""
    try:
        log: Any = json.loads((folder / HISTORY / _STATES).read_text(encoding="utf-8"))
        states = log["states"]
        at = int(log["at"])
        if isinstance(states, list) and all(isinstance(s, dict) and "dir" in s for s in states):
            told = log.get("told")
            found = {"states": states, "at": min(at, len(states) - 1)}
            return {**found, "told": told} if isinstance(told, str) else found
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {"states": [], "at": -1}


def restore_state(folder: Path, state: dict[str, Any], pages: list[Path]) -> None:
    """Puts the state's pages and comments in place of the current ones."""
    source = folder / HISTORY / state["dir"]
    for page in pages:
        page.unlink()
    for saved in source.iterdir():
        shutil.copy2(saved, folder / saved.name)
    if not (source / _COMMENTS).is_file():
        (folder / _COMMENTS).unlink(missing_ok=True)


def set_position(folder: Path, at: int) -> None:
    _write_log(folder, {**read_log(folder), "at": at})


def mark_told(folder: Path, state: str) -> None:
    """Notes that coscribe was told about the pages as of `state` (a state's `dir`)."""
    _write_log(folder, {**read_log(folder), "told": state})


def _write_log(folder: Path, log: dict[str, Any]) -> None:
    path = folder / HISTORY / _STATES
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(log, indent=1), encoding="utf-8")


def _digest(folder: Path, pages: list[Path]) -> str:
    digest = hashlib.sha256()
    for page in [*pages, folder / _COMMENTS]:
        if page.is_file():
            digest.update(page.name.encode() + b"\0" + page.read_bytes() + b"\0")
    return digest.hexdigest()
