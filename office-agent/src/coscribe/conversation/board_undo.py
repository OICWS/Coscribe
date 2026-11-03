"""Undo for the edits the canvas's properties panel writes into an artboard's page.

Before each edit the page's source is kept, with a hash of what the edit wrote. Undo puts the kept
source back only while the page is still exactly what the panel wrote: once coscribe (or anything
else) has written the page since, its work would be lost, so undo refuses instead.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .board_edits import BoardEditError, note_board_undo

_FOLDER = "design_undo"
_KEPT = 20


class NothingToUndo(BoardEditError):
    """The page has no edit from the panel to take back."""


class PageWrittenSince(BoardEditError):
    """The page was written by something else after the panel's last edit."""


def _stack(page: Path, state_dir: Path) -> Path:
    key = hashlib.sha1(os.path.normcase(str(page.resolve())).encode("utf-8")).hexdigest()[:20]
    return state_dir / _FOLDER / f"{key}.json"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(stack: Path) -> list[dict[str, str]]:
    try:
        entries = json.loads(stack.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return entries if isinstance(entries, list) else []


def _write(stack: Path, entries: list[dict[str, str]]) -> None:
    if not entries:
        stack.unlink(missing_ok=True)
        return
    stack.parent.mkdir(parents=True, exist_ok=True)
    stack.write_text(json.dumps(entries[-_KEPT:], ensure_ascii=False), encoding="utf-8")


def keep_for_undo(page: Path, before: str, said: str, state_dir: Path) -> None:
    """Called after an edit was written: keep the source from before it, and what it wrote."""
    stack = _stack(page, state_dir)
    after = page.read_text(encoding="utf-8")
    _write(stack, [*_read(stack), {"before": before, "after": _digest(after), "said": said}])


def undo_board_edit(page: Path, state_dir: Path) -> int:
    """Put back the page as it was before the panel's last edit; how many edits remain to undo."""
    stack = _stack(page, state_dir)
    entries = _read(stack)
    if not entries:
        raise NothingToUndo("There is no edit from the panel to undo on this page")
    last = entries[-1]
    if _digest(page.read_text(encoding="utf-8")) != last["after"]:
        # What came before cannot be put back over another writer's work either.
        _write(stack, [])
        raise PageWrittenSince("The page was written since the last edit, so it is not undone")
    page.write_text(last["before"], encoding="utf-8")
    _write(stack, entries[:-1])
    note_board_undo(page, last["said"], state_dir)
    return len(entries) - 1
