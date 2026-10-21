"""The decks, documents and spreadsheets a conversation made, for the Artifacts page: each one's
kind, name, time and, for a document, its opening lines.

What counts is what the conversation's Outputs list says it made or changed
(`activity.summarize_activity`); the files themselves are read fresh, so a deck edited in the
Slides panel shows its new time."""

from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage

from ..runtime import ToolMetadata
from ..tools import WorkspaceScope
from .activity import summarize_activity

ARTIFACT_KINDS = {".pptx": "slides", ".docx": "docs", ".xlsx": "sheets"}
_EXCERPT_CHARS = 280


def _kind(name: str) -> str | None:
    # Word and PowerPoint leave a `~$name` lock file beside a file that is open.
    return None if name.startswith("~$") else ARTIFACT_KINDS.get(Path(name).suffix.lower())


def artifact_paths(
    messages: list[BaseMessage], catalog: dict[str, ToolMetadata], scope: WorkspaceScope
) -> list[tuple[str, str]]:
    """`(path, action)` of each artifact the messages made or changed, action being "created" or
    "edited", most recently touched first."""
    outputs = summarize_activity(messages, catalog, scope)["outputs"]
    return [(o["path"], o["action"]) for o in outputs if o["exists"] and _kind(o["name"])]


def describe_artifact(scope: WorkspaceScope, path: str) -> dict[str, Any] | None:
    """The artifact at `path` as it is on disk now, None when it is gone or not one."""
    kind = _kind(Path(path).name)
    if kind is None:
        return None
    try:
        resolved = scope.resolve(path)
    except (PermissionError, OSError, ValueError):
        return None
    if not resolved.is_file():
        return None
    stat = resolved.stat()
    return {
        "path": scope.relative(resolved),
        "location": str(resolved),
        "name": resolved.stem,
        "kind": kind,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "excerpt": _excerpt(str(resolved), stat.st_mtime_ns) if kind == "docs" else None,
    }


# A document's excerpt by file and version; the whole table goes when it grows large.
_excerpts: dict[tuple[str, int], dict[str, str] | None] = {}


def _excerpt(location: str, modified_ns: int) -> dict[str, str] | None:
    key = (location, modified_ns)
    if key not in _excerpts:
        if len(_excerpts) >= 256:
            _excerpts.clear()
        _excerpts[key] = _read_excerpt(location)
    return _excerpts[key]


def _read_excerpt(location: str) -> dict[str, str] | None:
    """A document's first line and what follows it, None for a file that does not open."""
    # Loaded on first use: python-docx is slow to import and most runs never list a document.
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError

    try:
        paragraphs = [p.text.strip() for p in Document(location).paragraphs]
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, PackageNotFoundError):
        return None
    lines = [text for text in paragraphs if text]
    if not lines:
        return None
    return {"heading": lines[0][:120], "text": " ".join(lines[1:])[:_EXCERPT_CHARS]}
