"""Undo and redo for the edits the canvas's properties panel writes into an artboard's page.

Each step keeps the page's source from before it and a hash of what it wrote. A step is taken back
(or done again) only while the page is still exactly what the panel last wrote: once coscribe (or
anything else) has written the page since, its work would be lost, so the panel refuses and drops
the steps it kept for that page. A new edit drops the steps there were to redo.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .board_edits import BoardEditError, note_board_undo

_FOLDER = "design_undo"
_KEPT = 20

Step = dict[str, str]


class NothingToUndo(BoardEditError):
    """The page has no step from the panel to take back, or to do again."""


class PageWrittenSince(BoardEditError):
    """The page was written by something else after the panel's last step."""


def _file(page: Path, state_dir: Path) -> Path:
    key = hashlib.sha1(os.path.normcase(str(page.resolve())).encode("utf-8")).hexdigest()[:20]
    return state_dir / _FOLDER / f"{key}.json"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(file: Path) -> tuple[list[Step], list[Step], str]:
    """The steps to undo (each the source before it), to redo (each the source it undid), and a
    hash of what the panel last wrote."""
    try:
        kept = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], [], ""
    if not isinstance(kept, dict):
        return [], [], ""
    return list(kept.get("undo") or []), list(kept.get("redo") or []), str(kept.get("now") or "")


def _write(file: Path, undo: list[Step], redo: list[Step], now: str) -> None:
    if not undo and not redo:
        file.unlink(missing_ok=True)
        return
    file.parent.mkdir(parents=True, exist_ok=True)
    kept = {"undo": undo[-_KEPT:], "redo": redo[-_KEPT:], "now": now}
    file.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")


def keep_for_undo(page: Path, before: str, said: str, state_dir: Path) -> None:
    """Called after an edit was written: keep the source from before it."""
    file = _file(page, state_dir)
    undo, _, _ = _read(file)
    now = _digest(page.read_text(encoding="utf-8"))
    _write(file, [*undo, {"source": before, "said": said}], [], now)


def steps_left(page: Path, state_dir: Path) -> dict[str, int]:
    """How many steps can be undone and redone on the page as it is now: none once something
    other than the panel has written it."""
    undo, redo, now = _read(_file(page, state_dir))
    if not now or _digest(page.read_text(encoding="utf-8")) != now:
        return {"undo": 0, "redo": 0}
    return {"undo": len(undo), "redo": len(redo)}


def _step(page: Path, state_dir: Path, *, redo: bool) -> dict[str, int]:
    file = _file(page, state_dir)
    undo_steps, redo_steps, now = _read(file)
    taking, giving = (redo_steps, undo_steps) if redo else (undo_steps, redo_steps)
    if not taking:
        raise NothingToUndo("There is no step from the panel to take on this page")
    current = page.read_text(encoding="utf-8")
    if _digest(current) != now:
        _write(file, [], [], "")
        raise PageWrittenSince("The page was written since the panel's last step")
    step = taking.pop()
    page.write_text(step["source"], encoding="utf-8")
    giving.append({"source": current, "said": step["said"]})
    _write(file, undo_steps, redo_steps, _digest(step["source"]))
    note_board_undo(page, step["said"], state_dir, redone=redo)
    return {"undo": len(undo_steps), "redo": len(redo_steps)}


def undo_board_edit(page: Path, state_dir: Path) -> dict[str, int]:
    """Put back the page as it was before the panel's last edit; the steps left either way."""
    return _step(page, state_dir, redo=False)


def redo_board_edit(page: Path, state_dir: Path) -> dict[str, int]:
    """Do again the edit the panel last undid; the steps left either way."""
    return _step(page, state_dir, redo=True)
