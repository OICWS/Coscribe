"""Undo and redo in the Slides panel (design §9): the deck's pages put back as an earlier or later
build left them (`history`), and the deck built from them, under the deck's lock and refused
when the .pptx was changed outside coscribe, as every other change from the panel is."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...._file_locks import file_lock
from .build import MANIFEST, _read_manifest, _refuse_if_changed, build_deck, page_files
from .history import read_log, restore_state, set_position
from .view import NotBuiltFromPages, pages_folder


def deck_history(deck: Path) -> dict[str, Any]:
    """What undo and redo would do now: who made the change each would take back or bring back
    ("coscribe" or "you"), None where there is none."""
    folder = _folder(deck)
    log = read_log(folder)
    states, at = log["states"], log["at"]
    return {
        "undo": states[at]["by"] if at > 0 else None,
        "redo": states[at + 1]["by"] if 0 <= at < len(states) - 1 else None,
    }


def step_history(deck: Path, direction: int, *, resource_root: Path) -> dict[str, Any]:
    """Undo (`direction` -1) or redo (+1) one change. Raises ValueError when there is none."""
    folder = _folder(deck)
    with file_lock(deck):
        log = read_log(folder)
        target = log["at"] + direction
        if log["at"] < 0 or not 0 <= target < len(log["states"]):
            raise ValueError("nothing to undo" if direction < 0 else "nothing to redo")
        _refuse_if_changed(deck, _read_manifest(folder / MANIFEST))
        restore_state(folder, log["states"][target], page_files(folder, (".svg", ".html")))
        build_deck(folder, deck, resource_root=resource_root, recorded_as=None)
        set_position(folder, target)
    return deck_history(deck)


def _folder(deck: Path) -> Path:
    folder = pages_folder(deck)
    if folder is None:
        raise NotBuiltFromPages(f"{deck.name} was not built from pages")
    return folder
