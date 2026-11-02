"""The files a "folder" task has already started runs for (decision 0034), so each new file
starts one run. One JSON file per task next to its memory: the folder and pattern it watched,
and `{name: [modified, size]}` for each file it has seen.

The first look takes what is already there as seen, so saving a task never starts a run for
every old file. A file counts once it stopped changing for a few seconds, so a run never reads
half a download; one replaced by a newer file of the same name counts again."""

from __future__ import annotations

import fnmatch
import json
import os
import time
from pathlib import Path
from typing import Any

# How long a file must stay unchanged to count as written; the wait step uses the same.
SETTLE_SECONDS = 5
# A folder that fills up at once starts this many runs a check, the rest at the next ones.
MAX_NEW_PER_CHECK = 5
# What a browser or an editor writes before the real file appears.
_PARTIAL = (".tmp", ".crdownload", ".part", ".partial", ".download")


def _watched(name: str, pattern: str) -> bool:
    lowered = name.casefold()
    if lowered.startswith((".", "~$")) or lowered.endswith(_PARTIAL):
        return False
    return fnmatch.fnmatchcase(lowered, (pattern or "*").casefold())


class FolderWatch:
    def __init__(self, state_dir: str | Path) -> None:
        self.root = Path(state_dir) / "task_memory"

    def new_files(self, trigger_id: str, folder: str, pattern: str) -> list[str]:
        """The files in `folder` matching `pattern` that are written and not yet seen, oldest
        first, now marked seen. Empty when the folder is missing or this is the first look."""
        try:
            files = {
                entry.name: [entry.stat().st_mtime, entry.stat().st_size]
                for entry in os.scandir(folder)
                if entry.is_file() and _watched(entry.name, pattern)
            }
        except OSError:
            return []
        state = self._read(trigger_id)
        if state.get("folder") != folder or state.get("pattern") != pattern:
            self._write(trigger_id, {"folder": folder, "pattern": pattern, "seen": files})
            return []
        seen: dict[str, Any] = state.get("seen") or {}
        settled = time.time() - SETTLE_SECONDS
        new = sorted(
            (stamp[0], name)
            for name, stamp in files.items()
            if seen.get(name) != stamp and stamp[0] <= settled
        )[:MAX_NEW_PER_CHECK]
        # Names no longer there are dropped, so the list stays as long as the folder.
        kept = {name: stamp for name, stamp in seen.items() if name in files}
        kept.update({name: files[name] for _, name in new})
        if new or kept != seen:
            self._write(trigger_id, {"folder": folder, "pattern": pattern, "seen": kept})
        return [str(Path(folder) / name) for _, name in new]

    def forget(self, trigger_id: str) -> None:
        self._path(trigger_id).unlink(missing_ok=True)

    def _read(self, trigger_id: str) -> dict[str, Any]:
        try:
            data = json.loads(self._path(trigger_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, trigger_id: str, state: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(trigger_id)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, path)

    def _path(self, trigger_id: str) -> Path:
        return self.root / f"{trigger_id}.folder.json"
