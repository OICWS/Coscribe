"""What a scheduled task remembers from one run to the next (decision 0034): one JSON file per
task, `{name: {"value", "at", "by"}}`, where `by` is the run that kept the value or "you".

A run's remember steps only stage values; `keep` writes them once the run has finished, so a
failed, stopped or test run never moves the memory on. Not under `scheduled_tasks/`, whose
`*.json` files are the tasks themselves."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ...workflow_spec import MemoryEntry, memory_value

BY_PERSON = "you"


class TaskMemory:
    def __init__(self, state_dir: str | Path) -> None:
        self.root = Path(state_dir) / "task_memory"

    def entries(self, trigger_id: str) -> dict[str, dict[str, Any]]:
        path = self._path(trigger_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {str(k): v for k, v in data.items() if isinstance(v, dict) and "value" in v}

    def values(self, trigger_id: str) -> dict[str, Any]:
        return {name: entry["value"] for name, entry in self.entries(trigger_id).items()}

    def keep(self, trigger_id: str, values: dict[str, Any], by: str) -> None:
        """Write what a finished run's remember steps staged."""
        if not values:
            return
        entries = self.entries(trigger_id)
        at = datetime.now().isoformat(timespec="seconds")
        for name, value in values.items():
            entries[name] = {"value": value, "at": at, "by": by}
        self._write(trigger_id, entries)

    def set(self, trigger_id: str, declared: list[MemoryEntry], name: str, value: Any) -> None:
        """A person's own value for `name`, checked against what the task declares; a blank
        value forgets it, so the next run reads the entry's starting value."""
        entry = next((m for m in declared if m.name == name), None)
        if entry is None:
            raise KeyError(f"This task doesn't remember {name!r}")
        kept = memory_value(name, entry.type, value)
        entries = self.entries(trigger_id)
        if kept is None:
            entries.pop(name, None)
        else:
            at = datetime.now().isoformat(timespec="seconds")
            entries[name] = {"value": kept, "at": at, "by": BY_PERSON}
        self._write(trigger_id, entries)

    def delete(self, trigger_id: str) -> None:
        self._path(trigger_id).unlink(missing_ok=True)

    def _write(self, trigger_id: str, entries: dict[str, dict[str, Any]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(trigger_id)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, path)

    def _path(self, trigger_id: str) -> Path:
        return self.root / f"{trigger_id}.json"
