"""A Doc on disk, for the editor (decision 0025): read as blocks with the version of the file, and
saved as edits to named blocks. A save over a file that changed since the editor read it is refused,
as for a Word file (decision 0019); the per-block text each edit carries is the second guard."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from ..._file_locks import file_lock, replace_with_retry
from .blocks import BlocksRefused, Delete, Edit, Insert, Replace, apply_edits, read_doc

_MAX_BYTES = 5 * 1024 * 1024


class DocFileChanged(Exception):
    """The file changed since the editor read it; it has to be read again."""


def version_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


def side_folder(path: Path) -> Path:
    """The folder beside a Doc that holds what is not its text: kept versions, and later its
    comments and pictures (decision 0025)."""
    return path.with_suffix(".doc")


def _read_text(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    if len(data) > _MAX_BYTES:
        raise ValueError("This Doc is too large to edit here")
    return data, data.decode("utf-8")


def read_doc_file(path: Path) -> dict[str, Any]:
    """The Doc's version, title and blocks (`index`, `kind`, `text`). `NotADoc` for a markdown
    file without the marker, `ValueError` for one that is not text."""
    data, source = _read_text(path)
    doc = read_doc(source)
    heading = next((b.text.lstrip("# ").strip() for b in doc.blocks if b.kind == "heading"), "")
    return {
        "version": version_of(data),
        "title": str(doc.meta.get("title") or heading or path.stem),
        "blocks": [{"index": b.index, "kind": b.kind, "text": b.text} for b in doc.blocks],
    }


def _edit_of(raw: Any) -> Edit:
    if not isinstance(raw, dict):
        raise BlocksRefused("An edit is an object")
    op = raw.get("op")
    try:
        if op == "replace":
            return Replace(int(raw["index"]), str(raw["expected"]), str(raw["text"]))
        if op == "insert":
            return Insert(int(raw["after"]), str(raw["text"]))
        if op == "delete":
            return Delete(int(raw["index"]), str(raw["expected"]))
    except (KeyError, TypeError, ValueError):
        raise BlocksRefused("An edit is missing a field") from None
    raise BlocksRefused("An edit is replace, insert or delete")


def _write_atomically(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(text.encode("utf-8"))
    replace_with_retry(tmp, path)


def save_doc_edits(path: Path, version: str, edits: list[Any]) -> dict[str, Any]:
    """Applies the editor's edits to the file it read at `version` and returns the file read
    again. `DocFileChanged` over a newer file; `BlocksRefused`, with nothing written, for an edit
    that cannot apply."""
    parsed = [_edit_of(raw) for raw in edits]
    with file_lock(path):
        data, source = _read_text(path)
        if version_of(data) != version:
            raise DocFileChanged
        _write_atomically(path, apply_edits(source, parsed))
    return read_doc_file(path)
