"""A deck's files on disk: the .pptx and the pages folder whose build wrote it. The folder's
record names the deck relative to itself, so the two can move together (a renamed or synced
workspace); it is rewritten whenever the deck alone moves or is copied."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.exc import PackageNotFoundError

MANIFEST = "build.json"


def read_manifest(path: Path) -> dict[str, Any]:
    """The last build's record, with its deck as an absolute path; one that is missing or not
    in the shape this module writes counts as no build, so the deck at its path is treated as
    not built from these pages."""
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
    return {**data, "deck": str((path.parent / data["deck"]).resolve())}


def write_manifest(folder: Path, record: dict[str, Any]) -> None:
    try:
        deck = os.path.relpath(record["deck"], folder.resolve())
    except ValueError:  # another drive on Windows
        deck = record["deck"]
    (folder / MANIFEST).write_text(
        json.dumps({**record, "deck": deck}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def slide_hashes(deck: Path) -> list[str]:
    """One hash per slide over its XML and everything it points to, so a changed picture
    counts as a changed slide too."""
    hashes = []
    for slide in Presentation(str(deck)).slides:
        digest = hashlib.sha256(slide.part.blob)
        for rel in sorted(slide.part.rels.values(), key=lambda r: r.rId):
            digest.update(f"{rel.rId} {rel.reltype} {rel.target_ref}".encode())
            if not rel.is_external:
                digest.update(rel.target_part.blob)
        hashes.append(digest.hexdigest())
    return hashes


def pages_folder(deck: Path) -> Path | None:
    """The folder next to `deck` whose build wrote it, whether or not it changed since. A deck
    renamed outside coscribe (in Explorer, by a script) is found again by its slides, when a
    folder's recorded deck is gone and its last build wrote exactly these slides."""
    target = deck.resolve()
    orphans: list[tuple[Path, dict[str, Any]]] = []
    for folder in deck.parent.iterdir():
        manifest = read_manifest(folder / MANIFEST) if folder.is_dir() else {}
        if not manifest:
            continue
        if Path(manifest["deck"]) == target:
            return folder
        if not Path(manifest["deck"]).exists():
            orphans.append((folder, manifest))
    if not orphans or not deck.is_file():
        return None
    try:
        slides = slide_hashes(deck)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, PackageNotFoundError):
        return None
    matches = [f for f, m in orphans if [e["slide"] for e in m["pages"]] == slides]
    if len(matches) != 1:
        return None
    _point_record_at(matches[0], deck)
    return matches[0]


def deck_files(deck: Path) -> list[Path]:
    """The deck and, when a build of pages wrote it, that folder."""
    folder = pages_folder(deck)
    return [deck] if folder is None else [deck, folder]


def _point_record_at(folder: Path, deck: Path) -> None:
    write_manifest(folder, {**read_manifest(folder / MANIFEST), "deck": str(deck.resolve())})


def move_deck(deck: Path, target: Path) -> None:
    """Moves the deck, over `target` when it exists. Its pages folder follows it to another
    folder (only a folder beside the deck is looked at), and stays put for a rename."""
    folder = pages_folder(deck)
    replaced = pages_folder(target) if target.exists() else None
    deck.replace(target)
    # Two records naming one deck would let whichever folder is listed first answer for it.
    if replaced is not None and replaced != folder:
        (replaced / MANIFEST).unlink(missing_ok=True)
    if folder is None:
        return
    if folder.parent.resolve() != target.parent.resolve():
        moved = _free_name(target.parent / folder.name, target.stem)
        shutil.move(str(folder), str(moved))
        folder = moved
    _point_record_at(folder, target)


def _free_name(folder: Path, stem: str) -> Path:
    if not folder.exists():
        return folder
    twin = folder.with_name(f"{folder.name} ({stem})")
    n = 2
    while twin.exists():
        twin = folder.with_name(f"{folder.name} ({stem} {n})")
        n += 1
    return twin


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
