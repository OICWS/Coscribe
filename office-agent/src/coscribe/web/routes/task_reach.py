"""What a scheduled task can reach (decision 0048): its workspace's folder, the Allowed folders
that workspace uses (decision 0053), and the folders allowed for this task only. The task's form
shows them, and a folder input is checked against them before a run would stop to ask."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...runtime import DEFAULT_ENVIRONMENT, Environments
from ...runtime_lg import AuditLog, record_decision
from ...tools import ScheduledTriggerStore
from ..state import AppState


def _missing(trigger_id: str) -> JSONResponse:
    return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)


def _allowed(settings: Any, folders: list[str]) -> list[dict[str, str]]:
    """The Allowed folders the workspace uses, each with the most it permits (decision 0053)."""
    words = {"read": "read", "read-write": "write", "read-write-delete": "delete"}
    found = [(folder, settings.allowed_access(Path(folder)) or "read-write") for folder in folders]
    return [{"path": f, "permission": words[access]} for f, access in found]


def _within(path: Path, root: str) -> bool:
    try:
        return path.is_relative_to(Path(root).resolve())
    except OSError:
        return False


def reach_of(settings: Any, env_id: str, task_folders: list[str]) -> dict[str, Any]:
    environment = Environments(settings.state_dir).get(env_id)
    folders = list(environment["folders"]) if environment else []
    return {
        "workspace": {
            "id": env_id,
            "name": environment["name"] if environment else env_id,
            # The default workspace with no folder of its own works in Coscribe's folder.
            "folders": folders[:1] or [str(Path(settings.workspace_root).resolve())],
        },
        "allowed": _allowed(settings, folders[1:]),
        "task": task_folders,
    }


def where(reach: dict[str, Any], text: str) -> dict[str, Any]:
    """Which part of a reach holds a path: a relative one is taken from the workspace's folder,
    as the file tools take it. Writable says whether a run may save there without asking."""
    main = Path(reach["workspace"]["folders"][0])
    try:
        path = (main / Path(text.strip()).expanduser()).resolve()
    except (OSError, ValueError):
        return {"path": text, "inside": None, "root": None, "writable": False, "exists": False}
    found: dict[str, Any] = {"inside": None, "root": None, "writable": False}
    places = [
        *(("workspace", root, True) for root in reach["workspace"]["folders"]),
        *(("task", root, True) for root in reach["task"]),
        *(("allowed", a["path"], a["permission"] != "read") for a in reach["allowed"]),
    ]
    for inside, root, writable in places:
        if _within(path, root) and (
            found["inside"] is None or (writable and not found["writable"])
        ):
            found = {"inside": inside, "root": root, "writable": writable}
    return {"path": str(path), **found, "exists": path.is_dir()}


def reach_routes(router: APIRouter, state: AppState) -> None:
    settings = state.settings

    async def task_reach(trigger_id: str) -> JSONResponse:
        trigger = ScheduledTriggerStore(settings.state_dir).load(trigger_id)
        if trigger is None:
            return _missing(trigger_id)
        folders = list(trigger.permissions.get("folders", []))
        return JSONResponse(reach_of(settings, trigger.environment, folders))

    async def check_path(payload: dict[str, Any]) -> JSONResponse:
        """Where a folder an input names falls, for a saved task or a new one in a workspace."""
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(str(payload.get("task") or "")) if payload.get("task") else None
        env_id = trigger.environment if trigger else str(payload.get("environment") or "")
        folders = list(trigger.permissions.get("folders", [])) if trigger else []
        text = payload.get("path")
        if not isinstance(text, str) or not text.strip():
            return JSONResponse({"error": "path must name a folder."}, status_code=422)
        return JSONResponse(where(reach_of(settings, env_id or DEFAULT_ENVIRONMENT, folders), text))

    async def allow_folder(trigger_id: str, payload: dict[str, Any]) -> JSONResponse:
        """Only this task: its runs may read and write the folder from now on."""
        store = ScheduledTriggerStore(settings.state_dir)
        if store.load(trigger_id) is None:
            return _missing(trigger_id)
        text = str(payload.get("path") or "").strip()
        folder = Path(text).expanduser()
        if not text or not folder.is_absolute() or not folder.is_dir():
            return JSONResponse(
                {"error": f"{text or 'That'} isn't a folder on this computer."}, status_code=422
            )
        target = str(folder.resolve())
        trigger = store.grant(trigger_id, "folders", target)
        record_decision(
            AuditLog(settings.state_dir),
            thread_id=f"task:{trigger_id}",
            tool_name="allow_task_folder",
            arguments={"task": trigger_id, "folder": target},
            decision="approve",
            reason="human",
        )
        return JSONResponse({"task": trigger.permissions.get("folders", []) if trigger else []})

    async def remove_folder(trigger_id: str, path: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None:
            return _missing(trigger_id)
        folders = trigger.permissions.get("folders", [])
        if path in folders:
            folders.remove(path)
            store.save(trigger)
        return JSONResponse({"task": folders})

    base = "/api/scheduled-tasks/{trigger_id}"
    router.add_api_route(f"{base}/reach", task_reach, methods=["GET"])
    router.add_api_route(f"{base}/folders", allow_folder, methods=["POST"])
    router.add_api_route(f"{base}/folders", remove_folder, methods=["DELETE"])
    router.add_api_route("/api/reach/check", check_path, methods=["POST"])
