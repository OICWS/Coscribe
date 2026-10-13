"""The code module: download, status and permissions."""

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
)
from fastapi.responses import JSONResponse

from ....code_runtime.install import CodexUnavailable
from ....code_runtime.launch import codex_model
from ....code_runtime.permissions import CodePermissions
from ....code_runtime.service import (
    code_service,
)
from ....runtime_lg.code_agent import CODE_APPROVAL_RISKS
from ...state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings

    def _code_permissions() -> CodePermissions:
        return CodePermissions(settings.state_dir, tuple(CODE_APPROVAL_RISKS))

    @router.get("/api/code")
    async def code_status() -> dict[str, Any]:
        """The code module's download, and whether Codex can use the model
        a chat's code task would run on (the chat's own, unless one is set)."""
        service = code_service(settings)
        model = settings.code_model or settings.default_model
        try:
            codex_model(model, service.custom_providers())
            model_problem = None
        except CodexUnavailable as exc:
            model_problem = str(exc)
        return {**service.status(), "model": model, "model_problem": model_problem}

    @router.get("/api/code/permissions")
    async def get_code_permissions() -> dict[str, Any]:
        return _code_permissions().load()

    @router.put("/api/code/permissions")
    async def put_code_permissions(payload: dict[str, str]) -> Any:
        try:
            return _code_permissions().update(payload)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)

    @router.post("/api/code/install")
    async def install_code() -> Any:
        try:
            await code_service(settings).prepare()
        except Exception as exc:  # noqa: BLE001 -- a failed download is reported to the page
            return JSONResponse({"error": str(exc) or type(exc).__name__}, status_code=502)
        return await code_status()

    @router.delete("/api/code/install")
    async def remove_code() -> Any:
        if not await code_service(settings).remove():
            return JSONResponse(
                {"error": "The code module is working. Try again once it's done."},
                status_code=409,
            )
        return await code_status()

    return router
