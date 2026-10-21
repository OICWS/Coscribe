"""The versions of a document the Docs editor has held, so a change made behind it (by coscribe, in
Word) can be undone from the editor and done again (decision 0019). A version is kept the first time
the editor reads or saves it; the person's own edits since a version are one step, the editor's own
undo takes them back letter by letter."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from ..._file_locks import file_lock
from ._review import write_atomically
from .blocks import DocChanged, read_doc_blocks, version_of

_FOLDER = "docs_history"
_KEEP = 20
_MAX_BYTES = 25 * 1024 * 1024


class VersionGone(Exception):
    """The version asked for is no longer kept."""


def _folder_of(path: Path, state_dir: Path) -> Path:
    key = hashlib.sha1(os.path.normcase(str(path.resolve())).encode("utf-8")).hexdigest()[:20]
    return state_dir / _FOLDER / key


def _entries(folder: Path) -> list[dict[str, Any]]:
    try:
        found = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return found if isinstance(found, list) else []


def _store(folder: Path, entries: list[dict[str, Any]]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    kept = {e["version"] for e in entries}
    for old in folder.glob("*.docx"):
        if old.stem not in kept:
            old.unlink(missing_ok=True)
    (folder / "index.json").write_text(json.dumps(entries), encoding="utf-8")


def _keep(path: Path, state_dir: Path, data: bytes, source: str) -> str:
    version = version_of(data)
    if len(data) > _MAX_BYTES:
        return version
    folder = _folder_of(path, state_dir)
    with file_lock(folder):
        entries = _entries(folder)
        if entries and entries[-1]["version"] == version:
            return version
        # The person's saves while they type are one step; something else changing the file ends it.
        if source == "you" and entries and entries[-1]["source"] == "you":
            entries.pop()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{version}.docx").write_bytes(data)
        entries.append({"version": version, "source": source, "at": time.time()})
        _store(folder, entries[-_KEEP:])
    return version


def remember_version(path: Path, state_dir: Path, source: str) -> str:
    """Keeps the file as it is now (source: `seen` when the editor read it, `you` after its save,
    `restore` after an undo or redo) and returns its version."""
    return _keep(path, state_dir, path.read_bytes(), source)


def restore_version(path: Path, state_dir: Path, expected: str, target: str) -> dict[str, Any]:
    """Puts a kept version back as the file, over the version the editor holds; the version it
    replaces is kept, so the step can be taken back. `DocChanged` over a newer file, `VersionGone`
    for a version no longer kept."""
    with file_lock(path):
        current = path.read_bytes()
        if version_of(current) != expected:
            raise DocChanged
        kept = _folder_of(path, state_dir) / f"{target}.docx"
        if not target.isalnum() or not kept.is_file():
            raise VersionGone
        _keep(path, state_dir, current, "seen")
        write_atomically(path, kept.read_bytes())
    remember_version(path, state_dir, "restore")
    return read_doc_blocks(path)
