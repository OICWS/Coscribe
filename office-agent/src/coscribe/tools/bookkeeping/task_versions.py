"""Every workflow a scheduled task was saved with (decision 0035): one JSON file per task, a list
of `{"number", "saved_at", "how", "from"?, "workflow"}`, oldest first, the latest `MAX_VERSIONS`.

`how` is "created", "edited" (on its page), "conversation" (a draft saved from a conversation),
"restored" (with the version it came `from`) or "found": a task saved before versions were
kept, recorded as it was the first time it changes or runs. Beside them, `<id>.overview.json` holds
the sentence the simple view opens the task with."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ._trigger_files import trigger_file

MAX_VERSIONS = 50


def _same(left: Any, right: Any) -> bool:
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


class TaskVersions:
    def __init__(self, state_dir: str | Path) -> None:
        self.root = Path(state_dir) / "task_versions"

    def all(self, trigger_id: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(self._path(trigger_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [v for v in data if isinstance(v, dict) and isinstance(v.get("number"), int)]

    def current(self, trigger_id: str) -> int | None:
        versions = self.all(trigger_id)
        return versions[-1]["number"] if versions else None

    def get(self, trigger_id: str, number: int) -> dict[str, Any] | None:
        return next((v for v in self.all(trigger_id) if v["number"] == number), None)

    def keep(
        self,
        trigger_id: str,
        workflow: dict[str, Any] | None,
        how: str,
        restored_from: int | None = None,
    ) -> int | None:
        """The number of the version `workflow` is: the latest when it is the same, else a new
        one. None for a task without a workflow."""
        if workflow is None:
            return None
        versions = self.all(trigger_id)
        if versions and _same(versions[-1]["workflow"], workflow):
            return int(versions[-1]["number"])
        number = versions[-1]["number"] + 1 if versions else 1
        saved_at = datetime.now().isoformat(timespec="seconds")
        version: dict[str, Any] = {"number": number, "saved_at": saved_at, "how": how}
        version["workflow"] = workflow
        if restored_from is not None:
            version["from"] = restored_from
        self._write(trigger_id, [*versions, version][-MAX_VERSIONS:])
        return number

    def saved(
        self,
        trigger_id: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        how: str,
        restored_from: int | None = None,
    ) -> None:
        """Record a save; what a task held before versions were kept becomes its version 1."""
        if before is not None and not self.all(trigger_id):
            self.keep(trigger_id, before, "found")
        self.keep(trigger_id, after, how, restored_from)

    def overview(self, trigger_id: str) -> dict[str, Any] | None:
        """The sentence the simple view opens with: `{"text", "version", "by"}`, "by" being "ai"
        (written for that version) or "you" (kept whatever the version)."""
        try:
            data = json.loads(self._overview_path(trigger_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) and isinstance(data.get("text"), str) else None

    def set_overview(self, trigger_id: str, text: str, version: int, by: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._overview_path(trigger_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"text": text, "version": version, "by": by}, ensure_ascii=False),
                       encoding="utf-8")  # fmt: skip
        os.replace(tmp, path)

    def clear_overview(self, trigger_id: str) -> None:
        self._overview_path(trigger_id).unlink(missing_ok=True)

    def delete(self, trigger_id: str) -> None:
        self._path(trigger_id).unlink(missing_ok=True)
        self.clear_overview(trigger_id)

    def _write(self, trigger_id: str, versions: list[dict[str, Any]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(trigger_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(versions, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)

    def _path(self, trigger_id: str) -> Path:
        return trigger_file(self.root, trigger_id, ".json")

    def _overview_path(self, trigger_id: str) -> Path:
        return trigger_file(self.root, trigger_id, ".overview.json")
