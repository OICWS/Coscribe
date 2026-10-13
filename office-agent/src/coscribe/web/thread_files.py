"""A thread's files under the state dir: its title and workspace sidecars, and
which folders a new session opens in. Reads settings and the state dir, nothing
from FastAPI, so it runs without building the app."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import Settings
from ..runtime import SessionEnvironments
from ..tools import MessagingStore, ScheduledTriggerStore, parse_run_thread_id
from ..workflows import granted_by, parse_workflow


class ThreadFiles:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def title_sidecar_path(self, thread_id: str) -> Path:
        # Per-thread sidecar-file convention (plain text keyed by
        # thread_id under settings.state_dir) shared with
        # workspace_sidecar_path and the skills sidecar -- holds a
        # user-chosen rename, overriding list_threads' default
        # "preview = first human message" title. Unlike the workspace
        # sidecar, this one is never read to configure a live session --
        # it only affects how a thread is displayed in the nav rail's
        # session list.
        return self._settings.state_dir / f"{thread_id}.title"

    def workspace_sidecar_path(self, thread_id: str) -> Path:
        return self._settings.state_dir / f"{thread_id}.workspace"

    def write_workspace_sidecar(self, thread_id: str, folders: list[str]) -> None:
        if not folders:
            self.workspace_sidecar_path(thread_id).unlink(missing_ok=True)
            return
        self._settings.state_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_sidecar_path(thread_id).write_text(json.dumps(folders), encoding="utf-8")

    def read_workspace_sidecar(self, thread_id: str) -> list[str]:
        sidecar = self.workspace_sidecar_path(thread_id)
        if not sidecar.is_file():
            return []
        text = sidecar.read_text(encoding="utf-8").strip()
        # Threads from before multi-folder conversations hold one bare path.
        if not text.startswith("["):
            return [text] if text else []
        try:
            saved = json.loads(text)
        except json.JSONDecodeError:
            return []
        return [str(folder) for folder in saved if isinstance(folder, str) and folder]

    def delete(self, thread_id: str) -> None:
        """Every file that belongs to a thread -- otherwise a new thread later
        reusing the same id would inherit an old task list or workspace/skills
        choice."""
        (self._settings.state_dir / f"{thread_id}.tasks.json").unlink(missing_ok=True)
        self.workspace_sidecar_path(thread_id).unlink(missing_ok=True)
        self.title_sidecar_path(thread_id).unlink(missing_ok=True)
        SessionEnvironments(self._settings.state_dir).delete(thread_id)
        MessagingStore(self._settings.state_dir).delete(thread_id)

    def run_workspace(self, thread_id: str) -> str | None:
        """A scheduled run's thread works in its task's folder."""
        parsed = parse_run_thread_id(thread_id)
        if parsed is None:
            return None
        trigger = ScheduledTriggerStore(self._settings.state_dir).load(parsed[0])
        return trigger.workspace if trigger is not None else None

    def run_folders(self, thread_id: str) -> list[str]:
        """A scheduled run's folders: its task's own, then the existing
        ones its workflow names or the person allowed while a run waited."""
        parsed = parse_run_thread_id(thread_id)
        trigger = (
            ScheduledTriggerStore(self._settings.state_dir).load(parsed[0]) if parsed else None
        )
        if trigger is None:
            return []
        extra = list(trigger.permissions.get("folders", []))
        if trigger.workflow is not None:
            extra = [*granted_by(parse_workflow(trigger.workflow))["folders"], *extra]
        extra = [folder for folder in dict.fromkeys(extra) if Path(folder).is_dir()]
        if not extra:
            return [trigger.workspace] if trigger.workspace else []
        return [trigger.workspace or str(self._settings.workspace_root), *extra]

    def resolve_folders(self, thread_id: str, workspace_param: str | None) -> list[Path]:
        """The ?workspace= query param only counts the first time a thread
        is seen; after that the sidecar (changed through set_folders) wins.
        Empty means the app's default workspace -- kept distinct from an
        explicit choice of that same folder, which the UI shows as chosen."""
        if self.workspace_sidecar_path(thread_id).is_file():
            return [Path(folder) for folder in self.read_workspace_sidecar(thread_id)]
        run_folders = self.run_folders(thread_id)
        if run_folders and workspace_param is None:
            self.write_workspace_sidecar(thread_id, run_folders)
            return [Path(folder) for folder in run_folders]
        if workspace_param is None:
            workspace_param = self.run_workspace(thread_id)
        if not workspace_param:
            return []
        self.write_workspace_sidecar(thread_id, [workspace_param])
        return [Path(workspace_param)]
