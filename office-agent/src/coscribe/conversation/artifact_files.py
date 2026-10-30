"""What the Artifacts menu does to an artifact's file: rename it, copy it, move it to the
recycle bin. A deck is more than its .pptx, so these go through the files that belong to it."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..tools import copy_deck, deck_files, doc_side_folder, move_deck
from .dashboard import dashboard_folder
from .design_canvas import CANVAS_SUFFIX, canvas_folder, is_canvas


class ArtifactFileError(Exception):
    """A refusal; `reason` is its text for the person, written here and never a system error's."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _is_deck(path: Path) -> bool:
    return path.suffix.lower() == ".pptx"


def _ending(path: Path) -> str:
    return path.name[-len(CANVAS_SUFFIX) :] if is_canvas(path) else path.suffix


def _side_folder_of(path: Path) -> Path | None:
    """Where the folder that belongs to `path` is or would be: a Doc's (versions, comments,
    pictures), a canvas's artboards, a dashboard's datasets."""
    if is_canvas(path):
        return canvas_folder(path)
    if path.suffix.lower() == ".md":
        return doc_side_folder(path)
    if path.suffix.lower() in (".html", ".htm"):
        return dashboard_folder(path)
    return None


def _side_folder(path: Path) -> Path | None:
    folder = _side_folder_of(path)
    return folder if folder is not None and folder.is_dir() else None


def renamed_path(path: Path, name: str) -> Path:
    """Where `path` goes when it is named `name`: same folder and same ending."""
    ending = _ending(path)
    stem = name.strip()
    if stem.lower().endswith(ending.lower()):
        stem = stem[: -len(ending)].rstrip()
    if not stem or stem.startswith(".") or _FORBIDDEN.search(stem) or stem.endswith("."):
        raise ArtifactFileError("That name can't be used for a file")
    target = path.with_name(stem + ending)
    if target.exists() and not _same_file(target, path):
        raise ArtifactFileError(f"{target.name} already exists in that folder")
    folder, moved = _side_folder(path), _side_folder_of(target)
    if folder and moved is not None and moved.exists() and not _same_file(moved, folder):
        raise ArtifactFileError(f"{moved.name} already exists in that folder")
    return target


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.samefile(b)
    except OSError:
        return False


def rename_file(path: Path, name: str) -> Path:
    target = renamed_path(path, name)
    folder = _side_folder(path)
    if _is_deck(path):
        move_deck(path, target)
    else:
        path.rename(target)
    moved = _side_folder_of(target)
    if folder and moved is not None:
        folder.rename(moved)
    return target


def free_copy_path(path: Path) -> Path:
    """`name copy.ext`, then `name copy 2.ext`, the first that is free."""
    ending = _ending(path)
    stem = path.name[: -len(ending)] if ending else path.name

    def taken(candidate: Path) -> bool:
        folder = _side_folder_of(candidate)
        return candidate.exists() or (folder is not None and folder.exists())

    candidate = path.with_name(f"{stem} copy{ending}")
    n = 2
    while taken(candidate):
        candidate = path.with_name(f"{stem} copy {n}{ending}")
        n += 1
    return candidate


def copy_file(path: Path) -> Path:
    target = free_copy_path(path)
    if _is_deck(path):
        copy_deck(path, target)
    else:
        shutil.copy2(path, target)
    folder, copied = _side_folder(path), _side_folder_of(target)
    if folder and copied is not None:
        # A Doc's copy starts with the original's pictures but not its comments or kept versions.
        doc = path.suffix == ".md"
        ignore = shutil.ignore_patterns("comments.json", "versions") if doc else None
        shutil.copytree(folder, copied, ignore=ignore)
    return target


def trash_file(path: Path) -> None:
    """The file and what belongs to it, to the recycle bin."""
    # Loaded on first use: only a delete needs it.
    from send2trash import send2trash

    files = deck_files(path) if _is_deck(path) else [path]
    if folder := _side_folder(path):
        files = [*files, folder]
    for file in files:
        send2trash(str(file))
