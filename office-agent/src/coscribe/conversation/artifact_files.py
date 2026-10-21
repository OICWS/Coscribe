"""What the Artifacts menu does to an artifact's file: rename it, copy it, move it to the
recycle bin. A deck is more than its .pptx, so these go through the files that belong to it."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..tools import copy_deck, deck_files, move_deck


class ArtifactFileError(Exception):
    """A refusal; `reason` is its text for the person, written here and never a system error's."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _is_deck(path: Path) -> bool:
    return path.suffix.lower() == ".pptx"


def renamed_path(path: Path, name: str) -> Path:
    """Where `path` goes when it is named `name`: same folder and same ending."""
    stem = name.strip()
    if stem.lower().endswith(path.suffix.lower()):
        stem = stem[: -len(path.suffix)].rstrip()
    if not stem or stem.startswith(".") or _FORBIDDEN.search(stem) or stem.endswith("."):
        raise ArtifactFileError("That name can't be used for a file")
    target = path.with_name(stem + path.suffix)
    if target.exists() and not _same_file(target, path):
        raise ArtifactFileError(f"{target.name} already exists in that folder")
    return target


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.samefile(b)
    except OSError:
        return False


def rename_file(path: Path, name: str) -> Path:
    target = renamed_path(path, name)
    if _is_deck(path):
        move_deck(path, target)
    else:
        path.rename(target)
    return target


def free_copy_path(path: Path) -> Path:
    """`name copy.ext`, then `name copy 2.ext`, the first that is free."""
    candidate = path.with_name(f"{path.stem} copy{path.suffix}")
    n = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} copy {n}{path.suffix}")
        n += 1
    return candidate


def copy_file(path: Path) -> Path:
    target = free_copy_path(path)
    if _is_deck(path):
        copy_deck(path, target)
    else:
        shutil.copy2(path, target)
    return target


def trash_file(path: Path) -> None:
    """The file and what belongs to it, to the recycle bin."""
    # Loaded on first use: only a delete needs it.
    from send2trash import send2trash

    files = deck_files(path) if _is_deck(path) else [path]
    for file in files:
        send2trash(str(file))
