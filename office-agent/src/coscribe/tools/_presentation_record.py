"""A deck's files on disk: the .pptx and the pages folder whose build wrote it. The folder's
record names the deck by path, so it is rewritten whenever the deck moves or is copied."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

MANIFEST = "build.json"


def read_manifest(path: Path) -> dict[str, Any]:
    """The last build's record; one that is missing or not in the shape this module writes
    counts as no build, so the deck at its path is treated as not built from these pages."""
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or not isinstance(data.get("deck"), str):
        return {}
    entries = data.get("pages")
    keys = {"page", "source", "slide"}
    if not isinstance(entries, list) or not all(
        isinstance(e, dict) and keys <= e.keys() for e in entries
    ):
        return {}
    return dict(data)


def pages_folder(deck: Path) -> Path | None:
    """The folder next to `deck` whose build wrote it, whether or not it changed since."""
    target = deck.resolve()
    for folder in deck.parent.iterdir():
        manifest = read_manifest(folder / MANIFEST) if folder.is_dir() else {}
        if manifest and Path(manifest["deck"]).resolve() == target:
            return folder
    return None


def deck_files(deck: Path) -> list[Path]:
    """The deck and, when a build of pages wrote it, that folder."""
    folder = pages_folder(deck)
    return [deck] if folder is None else [deck, folder]


def _point_record_at(folder: Path, deck: Path) -> None:
    record = read_manifest(folder / MANIFEST)
    record["deck"] = str(deck.resolve())
    (folder / MANIFEST).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def move_deck(deck: Path, target: Path) -> None:
    """Renames the deck, over `target` when it exists; its pages folder stays where it is and
    follows by its record."""
    folder = pages_folder(deck)
    replaced = pages_folder(target) if target.exists() else None
    deck.replace(target)
    # Two records naming one deck would let whichever folder is listed first answer for it.
    if replaced is not None and replaced != folder:
        (replaced / MANIFEST).unlink(missing_ok=True)
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
