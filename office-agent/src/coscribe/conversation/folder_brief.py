"""A few sentences on what a folder holds, so the model knows it from the first message instead
of listing it again in every conversation.

The brief is written once per folder, by the small side model, from the folder's file names and
types two levels deep; it reads no file. It is kept per folder (`folder-briefs.json` in the state
folder), shared by every conversation that works there, and written again when the names at the
top of the folder change. The model reads it in the conversation's context, beside the folder's
path: never in the system prompt, which providers cache.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import TAG_NOSTREAM

from ..runtime_lg import extract_text

logger = logging.getLogger(__name__)

BRIEF_INSTRUCTIONS = (
    "You describe a folder on someone's computer for an assistant that will work in it. From "
    "the listing of its files, write two or three plain sentences: what the folder is for, "
    "which subfolders or files are templates, data, finished work or other kinds, and how the "
    "files are named when there is a pattern. Name the subfolders as they are written. Don't "
    "guess at what files contain beyond what their names and types show, and don't list every "
    "file. Write in English. Reply with the sentences only."
)
MAX_BRIEF_CHARS = 900
# Folders that are tools' own, never the person's work.
_SKIP = frozenset({".git", ".coscribe", ".venv", "venv", "node_modules", "__pycache__", ".idea"})
_MAX_ENTRIES = 400
_EXAMPLES = 8


def _children(folder: Path) -> list[os.DirEntry[str]]:
    try:
        with os.scandir(folder) as entries:
            return sorted(
                (e for e in entries if e.name not in _SKIP and not e.name.startswith("~$")),
                key=lambda e: e.name.lower(),
            )
    except OSError:
        return []


def _signature(top: list[os.DirEntry[str]]) -> str:
    names = "\n".join(f"{e.name}/" if e.is_dir() else e.name for e in top)
    return hashlib.sha256(names.encode()).hexdigest()[:16]


def top_signature(folder: Path) -> str:
    """Changes when the names at the top of the folder do: then the brief is written again."""
    return _signature(_children(folder))


def folder_listing(folder: Path) -> tuple[str, str]:
    """What the side model reads (per folder, two levels deep: how many files of each type and a
    few names), and the folder's `top_signature`."""
    top = _children(folder)
    signature = _signature(top)
    lines: list[str] = []
    seen = 0

    def describe(where: str, entries: list[os.DirEntry[str]]) -> None:
        nonlocal seen
        files = [e for e in entries if e.is_file()]
        types = Counter(Path(e.name).suffix.lower() or "(no extension)" for e in files)
        counted = ", ".join(f"{n} {kind}" for kind, n in types.most_common(6))
        names = ", ".join(e.name for e in files[:_EXAMPLES])
        lines.append(
            f"{where}: {len(files)} files ({counted})" + (f"; e.g. {names}" if names else "")
        )
        seen += len(entries)

    describe("(top)", top)
    for entry in top:
        if seen >= _MAX_ENTRIES:
            lines.append("... more folders not listed")
            break
        if entry.is_dir():
            inner = _children(Path(entry.path))
            folders = [e.name for e in inner if e.is_dir()]
            describe(f"{entry.name}/", inner)
            if folders:
                lines[-1] += f"; subfolders: {', '.join(folders[:_EXAMPLES])}"
    return "\n".join(lines), signature


def clean_brief(text: str) -> str:
    brief = " ".join(text.split())
    return (
        brief[:MAX_BRIEF_CHARS].rsplit(" ", 1)[0] + "..." if len(brief) > MAX_BRIEF_CHARS else brief
    )


class FolderBriefs:
    """The briefs kept for every folder, by its path."""

    def __init__(self, state_dir: Path) -> None:
        self._path = Path(state_dir) / "folder-briefs.json"

    def _all(self) -> dict[str, dict[str, str]]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, folder: Path) -> dict[str, str] | None:
        return self._all().get(str(folder))

    def save(self, folder: Path, brief: str, signature: str) -> None:
        data = self._all()
        data[str(folder)] = {
            "brief": brief,
            "signature": signature,
            "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        partial = self._path.with_suffix(".json.part")
        partial.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        partial.replace(self._path)


async def write_brief(model: Any, folder: Path, briefs: FolderBriefs) -> str:
    """One short call outside the agent graph. An empty folder gets no brief."""
    listing, signature = await asyncio.to_thread(folder_listing, folder)
    if listing.startswith("(top): 0 files") and "\n" not in listing:
        briefs.save(folder, "", signature)
        return ""
    reply = await model.ainvoke(
        [
            SystemMessage(content=BRIEF_INSTRUCTIONS),
            HumanMessage(content=f"Folder: {folder.name}\n{listing}"),
        ],
        config={"tags": [TAG_NOSTREAM]},
    )
    brief = clean_brief(extract_text(reply.content))
    briefs.save(folder, brief, signature)
    return brief


class FolderBriefKeeper:
    """One conversation's view of the briefs: it starts writing those its folders lack or that
    are out of date, and adds the ones written to the conversation's context."""

    def __init__(
        self, state_dir: Path, side_model: Callable[[], Any], enabled: Callable[[], bool]
    ) -> None:
        self._briefs = FolderBriefs(state_dir)
        self._side_model = side_model
        self._enabled = enabled
        self._writing: dict[Path, asyncio.Task[str]] = {}
        # A failed call isn't tried again on its own until the folder changes: the panel asks
        # every few seconds while one is being written.
        self._failed: dict[Path, str] = {}

    def _stale(self, folder: Path) -> bool:
        kept = self._briefs.get(folder)
        signature = top_signature(folder)
        if self._failed.get(folder) == signature:
            return False
        return kept is None or kept.get("signature") != signature

    async def _write(self, folder: Path) -> str:
        try:
            return await write_brief(self._side_model(), folder, self._briefs)
        except Exception:
            self._failed[folder] = top_signature(folder)
            raise

    def refresh(self, folders: Sequence[Path], *, again: bool = False) -> list[asyncio.Task[str]]:
        """Starts the briefs to write, in the background; a failure only leaves one unwritten.
        Turned off (`Settings.folder_briefs`), only the person's own "Read again" writes one."""
        started: list[asyncio.Task[str]] = []
        if not again and not self._enabled():
            return started
        for folder in folders:
            running = self._writing.get(folder)
            if running is not None and not running.done():
                started.append(running)
                continue
            if not again and not self._stale(folder):
                continue
            task = asyncio.get_running_loop().create_task(self._write(folder))
            task.add_done_callback(_log_failure)
            self._writing[folder] = task
            started.append(task)
        return started

    async def reread(self, folder: Path) -> dict[str, Any]:
        """The person asked for the brief again."""
        for task in self.refresh([folder], again=True):
            with contextlib.suppress(Exception):
                await task
        return self.shown([folder])[0]

    def shown(self, folders: Sequence[Path]) -> list[dict[str, Any]]:
        """For the side panel: each folder's brief, or that one is being written. The panel asks
        when a conversation opens, so starting the missing ones here has them ready for the
        first message more often than waiting for it."""
        with contextlib.suppress(RuntimeError):
            self.refresh(folders)
        out = []
        for folder in folders:
            kept = self._briefs.get(folder) or {}
            writing = folder in self._writing and not self._writing[folder].done()
            out.append(
                {
                    "path": str(folder),
                    "name": folder.name,
                    "brief": kept.get("brief", ""),
                    "written_at": kept.get("written_at"),
                    "writing": writing,
                }
            )
        return out

    def context(self, described: str, folders: Sequence[Path]) -> str:
        """`described` (the conversation's folders and instructions) with the briefs there are;
        starts writing the missing ones, which the next message then carries."""
        with contextlib.suppress(RuntimeError):  # no loop: nothing can be written now
            self.refresh(folders)
        briefs = [(f, (self._briefs.get(f) or {}).get("brief", "")) for f in folders]
        lines = [f"- {folder.name} ({folder}): {brief}" for folder, brief in briefs if brief]
        if not lines:
            return described
        return described + "\n\nWhat the folders hold, from their file names:\n" + "\n".join(lines)


def _log_failure(task: asyncio.Task[str]) -> None:
    if not task.cancelled() and task.exception() is not None:
        logger.info("could not write a folder brief", exc_info=task.exception())
