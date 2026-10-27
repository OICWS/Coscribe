"""The Doc editor's routes: a markdown Doc read as blocks, the changed blocks saved back, and the
versions the editor kept (decision 0025). A Word file has its own routes (`docs.py`)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...tools import (
    DocBlocksRefused,
    DocFileChanged,
    DocVersionGone,
    NotADoc,
    read_doc_file,
    remember_doc_before_edit,
    remember_doc_version,
    restore_doc_version,
    save_doc_edits,
)
from ..schemas import DocFileSave, DocRestore
from ..state import AppState

# Fixed texts: a parser's own message can carry paths and internals.
_NO_DOC = "No Doc at that path"
_UNREADABLE = "This Doc could not be read"
_GONE = "That version is no longer kept"
_CHANGED = "This Doc changed since it was opened; it has been read again"


def _doc_file(state: AppState, thread_id: str, path: str, *, write: bool) -> Path | None:
    try:
        file = state.get_session(thread_id).workspace_scope().resolve(path, write=write)
    except (PermissionError, OSError, ValueError):
        return None
    return file if file.is_file() and file.suffix.lower() == ".md" else None


def _read_route(router: APIRouter, state: AppState) -> None:
    async def get_blocks(thread_id: str, path: str) -> JSONResponse:
        file = _doc_file(state, thread_id, path, write=False)
        if file is None:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            read = await asyncio.to_thread(read_doc_file, file)
            await asyncio.to_thread(remember_doc_version, file, "seen")
            return JSONResponse(read)
        except NotADoc:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        except Exception:  # a file that is not text raises more than one kind of error
            return JSONResponse({"error": _UNREADABLE}, status_code=422)

    router.add_api_route("/api/threads/{thread_id}/doc/blocks", get_blocks, methods=["GET"])


def _save_route(router: APIRouter, state: AppState) -> None:
    async def put_blocks(thread_id: str, body: DocFileSave) -> JSONResponse:
        file = _doc_file(state, thread_id, body.path, write=True)
        if file is None:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            # The file as it is before the first save since coscribe was told, to tell it later.
            await asyncio.to_thread(remember_doc_before_edit, file, state.settings.state_dir)
            await asyncio.to_thread(remember_doc_version, file, "seen")
            saved = await asyncio.to_thread(save_doc_edits, file, body.version, body.edits)
            await asyncio.to_thread(remember_doc_version, file, "you")
        except NotADoc:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        except DocFileChanged:
            return JSONResponse({"error": _CHANGED, "changed": True}, status_code=409)
        except DocBlocksRefused as refused:
            return JSONResponse({"error": refused.args[0]}, status_code=400)
        except Exception:
            return JSONResponse({"error": _UNREADABLE}, status_code=422)
        return JSONResponse(saved)

    router.add_api_route("/api/threads/{thread_id}/doc/blocks", put_blocks, methods=["PUT"])


def _restore_route(router: APIRouter, state: AppState) -> None:
    async def restore(thread_id: str, body: DocRestore) -> JSONResponse:
        file = _doc_file(state, thread_id, body.path, write=True)
        if file is None:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            restored = await asyncio.to_thread(restore_doc_version, file, body.version, body.to)
        except DocFileChanged:
            return JSONResponse({"error": _CHANGED, "changed": True}, status_code=409)
        except DocVersionGone:
            return JSONResponse({"error": _GONE}, status_code=404)
        except Exception:
            return JSONResponse({"error": _UNREADABLE}, status_code=422)
        return JSONResponse(restored)

    router.add_api_route("/api/threads/{thread_id}/doc/restore", restore, methods=["POST"])


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    _read_route(router, state)
    _save_route(router, state)
    _restore_route(router, state)
    return router
