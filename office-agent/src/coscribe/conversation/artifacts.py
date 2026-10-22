"""The decks, documents, spreadsheets and designs coscribe made, for the Artifacts page: a
registry of them that outlives the conversation that made each one, and each one's kind, name,
time and, for a document, its opening lines.

A conversation's Outputs list says what it made (`activity.summarize_activity`); the registry
adopts those files, and from then on an artifact is the file, not the conversation. Only files
the conversation created are adopted: one it merely edited, or one the person brought, is not
made by coscribe. The files themselves are read fresh, so a deck edited in the Slides panel
shows its new time."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage

from ..runtime import ToolMetadata
from ..tools import WorkspaceScope
from .activity import summarize_activity

ARTIFACT_KINDS = {
    ".pptx": "slides",
    ".docx": "docs",
    ".xlsx": "sheets",
    ".html": "design",
}
_EXCERPT_CHARS = 280


def _kind(name: str) -> str | None:
    # Word and PowerPoint leave a `~$name` lock file beside a file that is open.
    return None if name.startswith("~$") else ARTIFACT_KINDS.get(Path(name).suffix.lower())


def artifact_paths(
    messages: list[BaseMessage], catalog: dict[str, ToolMetadata], scope: WorkspaceScope
) -> list[str]:
    """The artifacts the messages created, most recently touched first."""
    outputs = summarize_activity(messages, catalog, scope)["outputs"]
    return [
        o["path"] for o in outputs if o["exists"] and o["action"] == "created" and _kind(o["name"])
    ]


def artifact_id(location: str) -> str:
    """The same file is the same artifact however it was reached."""
    return hashlib.sha1(os.path.normcase(location).encode("utf-8")).hexdigest()[:16]


class ArtifactRegistry:
    """The artifacts coscribe made: one JSON file under the state dir, each entry the file's
    location, the folders its conversation worked in (to open it again in a new one) and the
    conversation that made it."""

    def __init__(self, state_dir: str | Path) -> None:
        self._path = Path(state_dir) / "artifacts.json"

    def entries(self) -> list[dict[str, Any]]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return (
            [e for e in data if isinstance(e, dict) and "id" in e] if isinstance(data, list) else []
        )

    def get(self, artifact: str) -> dict[str, Any] | None:
        return next((e for e in self.entries() if e["id"] == artifact), None)

    def _save(self, entries: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._path)

    def adopt(self, locations: list[str], folders: list[str], thread_id: str) -> None:
        # Called on the event loop with no await between the read and the write, so two
        # adoptions cannot interleave.
        known = self.entries()
        have = {os.path.normcase(e["location"]) for e in known}
        added = [
            {
                "id": artifact_id(location),
                "location": location,
                "folders": folders,
                "thread_id": thread_id,
                "created_at": datetime.now().isoformat(),
            }
            for location in dict.fromkeys(locations)
            if os.path.normcase(location) not in have
        ]
        if added:
            self._save([*known, *added])

    def update(self, artifact: str, **fields: Any) -> None:
        """Changes an entry's fields, the id being the one thing that stays."""
        self._save([{**e, **fields} if e["id"] == artifact else e for e in self.entries()])

    def remove(self, artifact: str) -> None:
        self._save([e for e in self.entries() if e["id"] != artifact])


async def adopt_thread(
    registry: ArtifactRegistry,
    checkpointer: Any,
    thread_id: str,
    catalog: dict[str, ToolMetadata],
    scope: WorkspaceScope,
    folders: list[str],
) -> None:
    """Register what the conversation created, read from its checkpoint."""
    state = await checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
    messages = list(state.checkpoint["channel_values"].get("messages", [])) if state else []
    paths = await asyncio.to_thread(artifact_paths, messages, catalog, scope)
    found = [d["location"] for path in paths if (d := describe_artifact(scope, path))]
    registry.adopt(found, folders, thread_id)


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
