"""Settings › Capabilities: the optional LibreOffice, found or downloaded (decision 0026)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ....runtime_lg import AuditLog, record_decision
from ....tools import (
    LibreOfficeUnavailable,
    install_libreoffice,
    libreoffice_offer,
    libreoffice_status,
    remove_libreoffice,
)
from ...state import AppState

logger = logging.getLogger(__name__)


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    state_dir = state.settings.state_dir
    # The step a download is on ("" when none), so the row can say what it waits for and the
    # page can poll: the download request itself returns at once.
    job: dict[str, Any] = {"step": "", "done": 0, "total": 0, "problem": ""}
    running: set[asyncio.Task[None]] = set()

    def audit(action: str, error: str) -> None:
        record_decision(
            AuditLog(state_dir),
            thread_id="",
            tool_name=f"libreoffice_{action}",
            arguments={"error": error} if error else {},
            decision="reject" if error else "approve",
            reason="human",
        )

    def current() -> dict[str, Any]:
        return {
            **libreoffice_status(state_dir),
            "offer": libreoffice_offer(),
            "working": bool(job["step"]),
            **{key: job[key] for key in ("step", "done", "total", "problem")},
        }

    def download() -> None:
        error = ""
        try:
            install_libreoffice(
                state_dir,
                progress=lambda done, total: job.update(done=done, total=total),
                step=lambda name: job.update(step=name, done=0, total=0),
            )
        except LibreOfficeUnavailable as exc:
            error = exc.args[0] if exc.args else "LibreOffice could not be installed."
        except Exception:
            logger.exception("LibreOffice download failed")
            error = "LibreOffice could not be installed."
        audit("install", error)
        job.update(step="", problem=error)

    async def get_libreoffice() -> dict[str, Any]:
        # Asking a copy for its version starts it, which can take seconds.
        return await asyncio.to_thread(current)

    async def post_libreoffice() -> Any:
        if job["step"]:
            return JSONResponse(
                {"error": "LibreOffice is already being downloaded."}, status_code=409
            )
        job.update(step="download", done=0, total=0, problem="")
        task = asyncio.create_task(asyncio.to_thread(download))
        running.add(task)
        task.add_done_callback(running.discard)
        return await get_libreoffice()

    async def delete_libreoffice() -> Any:
        if job["step"]:
            return JSONResponse({"error": "LibreOffice is being downloaded."}, status_code=409)
        await asyncio.to_thread(remove_libreoffice, state_dir)
        audit("remove", "")
        job.update(problem="")
        return await get_libreoffice()

    router.add_api_route("/api/libreoffice", get_libreoffice, methods=["GET"])
    router.add_api_route("/api/libreoffice", post_libreoffice, methods=["POST"])
    router.add_api_route("/api/libreoffice", delete_libreoffice, methods=["DELETE"])
    return router
