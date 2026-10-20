"""What the user changed in a deck since coscribe last knew it (issue #462): coscribe's last build
or the last time it was told, against the pages now, from the undo history's recorded states. The
net difference is what counts, so an edit that was undone is not reported."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...._file_locks import file_lock
from .history import HISTORY, mark_told, read_log
from .view import pages_folder

_COMMENTS = "comments.json"


def deck_edits_since_coscribe(deck: Path) -> dict[str, Any] | None:
    """The pages the user edited, added and removed (file names) since coscribe built the deck or
    was last told, with the pages folder's name; None when there is nothing to tell, for a deck
    not built from pages or without a build of coscribe's to compare with. Reporting a change
    marks it told, so the next call has nothing until the user changes something again."""
    folder = pages_folder(deck)
    if folder is None:
        return None
    with file_lock(deck):
        log = read_log(folder)
        states, at = log["states"], log["at"]
        known = [
            i
            for i, s in enumerate(states[: at + 1])
            if s["by"] == "coscribe" or s["dir"] == log.get("told")
        ]
        if at < 0 or not known or known[-1] == at:
            return None
        before = _pages(folder / HISTORY / states[known[-1]]["dir"])
        after = _pages(folder / HISTORY / states[at]["dir"])
        edited = sorted(n for n in before.keys() & after.keys() if before[n] != after[n])
        added = sorted(after.keys() - before.keys())
        removed = sorted(before.keys() - after.keys())
        if not (edited or added or removed):
            return None
        mark_told(folder, states[at]["dir"])
    return {"folder": folder.name, "edited": edited, "added": added, "removed": removed}


def _pages(state: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in state.iterdir() if p.is_file() and p.name != _COMMENTS}
