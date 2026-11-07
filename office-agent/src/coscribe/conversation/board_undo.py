"""Undo and redo for the edits the canvas's properties panel writes into an artboard's page, or into
a part several pages share.

The steps are kept per canvas, so an edit is undone from any of its artboards, and each names the
file it wrote (a page or a part, both in the canvas folder) and keeps that file's source from
before it. A step is taken back (or done again) only while every file the panel wrote is still
exactly what it last wrote: once coscribe (or anything else) has written one since, its work would
be lost, so the panel refuses and drops the steps. A new edit drops the steps there were to redo.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .board_edits import BoardEditError, note_board_undo
from .design_canvas import canvas_of_page

_FOLDER = "design_undo"
_KEPT = 20

Step = dict[str, str]


class NothingToUndo(BoardEditError):
    """The canvas has no step from the panel to take back, or to do again."""


class PageWrittenSince(BoardEditError):
    """A file the panel wrote was written by something else after the panel's last step."""


def _record(page: Path, state_dir: Path) -> Path:
    owner = canvas_of_page(page) or page
    key = hashlib.sha1(os.path.normcase(str(owner.resolve())).encode("utf-8")).hexdigest()[:20]
    return state_dir / _FOLDER / f"{key}.json"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(record: Path) -> tuple[list[Step], list[Step], dict[str, str]]:
    """The steps to undo (each the source before it), to redo (each the source it undid), and a
    hash of what the panel last wrote into each file."""
    try:
        kept = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], [], {}
    if not isinstance(kept, dict) or not isinstance(kept.get("now"), dict):
        return [], [], {}
    return list(kept.get("undo") or []), list(kept.get("redo") or []), dict(kept["now"])


def _write(record: Path, undo: list[Step], redo: list[Step], now: dict[str, str]) -> None:
    if not undo and not redo:
        record.unlink(missing_ok=True)
        return
    record.parent.mkdir(parents=True, exist_ok=True)
    kept = {"undo": undo[-_KEPT:], "redo": redo[-_KEPT:], "now": now}
    record.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")


def _untouched(folder: Path, now: dict[str, str]) -> bool:
    for name, digest in now.items():
        try:
            if _digest((folder / name).read_text(encoding="utf-8")) != digest:
                return False
        except OSError:
            return False
    return bool(now)


def keep_for_undo(written: Path, before: str, said: str, state_dir: Path) -> None:
    """Called after an edit was written into a page or part: keep its source from before it."""
    record = _record(written, state_dir)
    undo, _, now = _read(record)
    # The file was just written by this edit, so its last state is the source from before it.
    others = {name: digest for name, digest in now.items() if name != written.name}
    unchanged = now.get(written.name, _digest(before)) == _digest(before)
    if not unchanged or (others and not _untouched(written.parent, others)):
        undo, now = [], {}
    now[written.name] = _digest(written.read_text(encoding="utf-8"))
    _write(record, [*undo, {"file": written.name, "source": before, "said": said}], [], now)


def steps_left(page: Path, state_dir: Path) -> dict[str, int]:
    """How many steps can be undone and redone on the page's canvas as it is now: none once
    something other than the panel has written one of the files it wrote."""
    undo, redo, now = _read(_record(page, state_dir))
    if not _untouched(page.parent, now):
        return {"undo": 0, "redo": 0}
    return {"undo": len(undo), "redo": len(redo)}


def _step(page: Path, state_dir: Path, *, redo: bool) -> dict[str, int]:
    record = _record(page, state_dir)
    undo_steps, redo_steps, now = _read(record)
    taking, giving = (redo_steps, undo_steps) if redo else (undo_steps, redo_steps)
    if not taking:
        raise NothingToUndo("There is no step from the panel to take on this canvas")
    if not _untouched(page.parent, now):
        _write(record, [], [], {})
        raise PageWrittenSince("A page was written since the panel's last step")
    step = taking.pop()
    target = page.parent / step.get("file", page.name)
    current = target.read_text(encoding="utf-8")
    target.write_text(step["source"], encoding="utf-8")
    giving.append({"file": target.name, "source": current, "said": step["said"]})
    now[target.name] = _digest(step["source"])
    _write(record, undo_steps, redo_steps, now)
    note_board_undo(target, step["said"], state_dir, redone=redo)
    return {"undo": len(undo_steps), "redo": len(redo_steps)}


def undo_board_edit(page: Path, state_dir: Path) -> dict[str, int]:
    """Put back the file the panel's last edit on this canvas wrote; the steps left either way."""
    return _step(page, state_dir, redo=False)


def redo_board_edit(page: Path, state_dir: Path) -> dict[str, int]:
    """Do again the edit the panel last undid; the steps left either way."""
    return _step(page, state_dir, redo=True)
