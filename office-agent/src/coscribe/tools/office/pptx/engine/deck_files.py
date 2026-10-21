"""A deck's files on disk: the .pptx and the pages folder whose build wrote it. The folder's
record names the deck by path, so it is rewritten whenever the deck moves or is copied."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .build import MANIFEST, _read_manifest
from .view import pages_folder


def deck_files(deck: Path) -> list[Path]:
    """The deck and, when a build of pages wrote it, that folder."""
    folder = pages_folder(deck)
    return [deck] if folder is None else [deck, folder]


def _point_record_at(folder: Path, deck: Path) -> None:
    record = _read_manifest(folder / MANIFEST)
    record["deck"] = str(deck.resolve())
    (folder / MANIFEST).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def move_deck(deck: Path, target: Path) -> None:
    """Renames the deck; its pages folder stays where it is and follows by its record."""
    folder = pages_folder(deck)
    deck.rename(target)
    if folder is not None:
        _point_record_at(folder, target)


def copy_deck(deck: Path, target: Path) -> None:
    """A second deck with its own copy of the pages folder, so editing one leaves the other."""
    folder = pages_folder(deck)
    shutil.copy2(deck, target)
    if folder is None:
        return
    twin = folder.with_name(f"{folder.name} ({target.stem})")
    n = 2
    while twin.exists():
        twin = folder.with_name(f"{folder.name} ({target.stem} {n})")
        n += 1
    shutil.copytree(folder, twin)
    _point_record_at(twin, target)
