"""The versions of a Doc the editor has held, so a change made behind it (by coscribe) can be undone
from the editor and done again (decision 0025, as 0019 does for Word files). They are kept in the
Doc's side folder: they travel with it. A version is kept the first time the editor reads or saves
it; the person's own saves since a version are one step."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..._file_locks import file_lock
from .files import DocFileChanged, _write_atomically, read_doc_file, side_folder, version_of

_KEEP = 20


class VersionGone(Exception):
    """The version asked for is no longer kept."""


def _folder(path: Path) -> Path:
    return side_folder(path) / "versions"


def _entries(folder: Path) -> list[dict[str, Any]]:
    try:
        found = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return found if isinstance(found, list) else []


def _store(folder: Path, entries: list[dict[str, Any]]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    kept = {e["version"] for e in entries}
    for old in folder.glob("*.md"):
        if old.stem not in kept:
            old.unlink(missing_ok=True)
    (folder / "index.json").write_text(json.dumps(entries), encoding="utf-8")


def _keep(path: Path, data: bytes, source: str) -> str:
    version = version_of(data)
    folder = _folder(path)
    with file_lock(folder):
        entries = _entries(folder)
        if entries and entries[-1]["version"] == version:
            return version
        # The person's saves while they type are one step; something else changing the file ends it.
        if source == "you" and entries and entries[-1]["source"] == "you":
            entries.pop()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{version}.md").write_bytes(data)
        entries.append({"version": version, "source": source, "at": time.time()})
        _store(folder, entries[-_KEEP:])
    return version


def remember_version(path: Path, source: str) -> str:
    """Keeps the file as it is now (source: `seen` when the editor read it, `you` after its save,
    `restore` after an undo or redo) and returns its version."""
    return _keep(path, path.read_bytes(), source)


def restore_version(path: Path, expected: str, target: str) -> dict[str, Any]:
    """Puts a kept version back as the file, over the version the editor holds; the version it
    replaces is kept, so the step can be taken back. `DocFileChanged` over a newer file,
    `VersionGone` for a version no longer kept."""
    with file_lock(path):
        current = path.read_bytes()
        if version_of(current) != expected:
            raise DocFileChanged
        kept = _folder(path) / f"{target}.md"
        if not target.isalnum() or not kept.is_file():
            raise VersionGone
        _keep(path, current, "seen")
        _write_atomically(path, kept.read_text(encoding="utf-8"))
    remember_version(path, "restore")
    return read_doc_file(path)
