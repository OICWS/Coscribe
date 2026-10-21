"""The Docs editor's routes: a .docx read as blocks, and the changed blocks saved back
(decision 0019)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...tools import (
    BlocksRefused,
    DocChanged,
    read_doc_blocks,
    remember_before_edit,
    save_doc_blocks,
)
from ..schemas import DocBlocksSave
from ..state import AppState

# Fixed texts: a parser's own message can carry paths and internals.
_NO_DOC = "No Word document at that path"
_UNREADABLE = "This document could not be read"
_CHANGED = "This document changed since it was opened; it has been read again"


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    def docx_file(thread_id: str, path: str, *, write: bool) -> Path | None:
        try:
            file = state.get_session(thread_id).workspace_scope().resolve(path, write=write)
        except (PermissionError, OSError, ValueError):
            return None
        return file if file.is_file() and file.suffix.lower() == ".docx" else None

    async def get_blocks(thread_id: str, path: str) -> JSONResponse:
        file = docx_file(thread_id, path, write=False)
        if file is None:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            return JSONResponse(await asyncio.to_thread(read_doc_blocks, file))
        except Exception:  # a file python-docx cannot open raises many kinds of error
            return JSONResponse({"error": _UNREADABLE}, status_code=422)

    async def put_blocks(thread_id: str, body: DocBlocksSave) -> JSONResponse:
        file = docx_file(thread_id, body.path, write=True)
        if file is None:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            # The file as it is before the first save since coscribe was told, to tell it later.
            await asyncio.to_thread(remember_before_edit, file, state.settings.state_dir)
            saved = await asyncio.to_thread(save_doc_blocks, file, body.version, body.blocks)
        except DocChanged:
            return JSONResponse({"error": _CHANGED, "changed": True}, status_code=409)
        except BlocksRefused as refused:
            return JSONResponse({"error": refused.args[0]}, status_code=400)
        except Exception:
            return JSONResponse({"error": _UNREADABLE}, status_code=422)
        return JSONResponse(saved)

    router.add_api_route("/api/threads/{thread_id}/docs/blocks", get_blocks, methods=["GET"])
    router.add_api_route("/api/threads/{thread_id}/docs/blocks", put_blocks, methods=["PUT"])
    return router
