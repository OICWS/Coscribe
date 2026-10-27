"""The Doc editor's routes: a markdown Doc read as blocks, the changed blocks saved back, the
versions the editor kept, and its comments (decision 0025). A Word file has its own routes
(`docs.py`)."""

from __future__ import annotations

import asyncio
import getpass
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...tools import (
    DocBlocksRefused,
    DocCommentNotFound,
    DocCommentRefused,
    DocFileChanged,
    DocVersionGone,
    NotADoc,
    add_doc_comment,
    delete_doc_comment,
    read_doc_comments,
    read_doc_file,
    remember_doc_before_edit,
    remember_doc_version,
    reply_to_doc_comment,
    resolve_doc_comment,
    restore_doc_version,
    save_doc_edits,
)
from ..schemas import (
    DocCommentNew,
    DocCommentReply,
    DocCommentState,
    DocFileSave,
    DocRestore,
)
from ..state import AppState

# Fixed texts: a parser's own message can carry paths and internals.
_NO_DOC = "No Doc at that path"
_UNREADABLE = "This Doc could not be read"
_GONE = "That version is no longer kept"
_CHANGED = "This Doc changed since it was opened; it has been read again"
# The texts of a refused comment: written here, so no exception's own text reaches the client.
_REFUSED_COMMENT = {
    "no_block": "There is no such block",
    "empty": "A comment needs some text",
    "too_long": "A comment holds 4000 characters at most",
}


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


def _author() -> str:
    # Word names a reviewer after the computer's user until one is set; comments do the same.
    return getpass.getuser()


async def _run(job: Callable[..., Any], *args: Any) -> Any:
    """`job` off the event loop, or the response its failure gets."""
    try:
        return await asyncio.to_thread(job, *args)
    except DocCommentNotFound:
        return JSONResponse({"error": "No such comment"}, status_code=404)
    except NotADoc:
        return JSONResponse({"error": _NO_DOC}, status_code=404)
    except DocCommentRefused as refused:
        return JSONResponse(
            {"error": _REFUSED_COMMENT.get(refused.code, "That comment cannot be made")},
            status_code=400,
        )
    except (ValueError, OSError):  # a file that is not text: its parser's message is not shown
        return JSONResponse({"error": _UNREADABLE}, status_code=422)


def _comment_routes(router: APIRouter, state: AppState) -> None:
    """The Doc's comments: read them, add one, reply, resolve or reopen, delete."""
    base = "/api/threads/{thread_id}/doc/comments"

    def _file(thread_id: str, path: str) -> Path | JSONResponse:
        file = _doc_file(state, thread_id, path, write=True)
        return JSONResponse({"error": _NO_DOC}, status_code=404) if file is None else file

    async def get_comments(thread_id: str, path: str) -> Any:
        file = _file(thread_id, path)
        return file if isinstance(file, JSONResponse) else await _run(read_doc_comments, file)

    async def post_comment(thread_id: str, body: DocCommentNew) -> Any:
        file = _file(thread_id, body.path)
        if isinstance(file, JSONResponse):
            return file
        return await _run(
            lambda: add_doc_comment(
                file, block=body.block, text=body.text, author=_author(), sent=body.sent
            )
        )

    async def post_reply(thread_id: str, comment_id: str, body: DocCommentReply) -> Any:
        file = _file(thread_id, body.path)
        if isinstance(file, JSONResponse):
            return file
        author = "coscribe" if body.from_coscribe else _author()
        return await _run(
            lambda: reply_to_doc_comment(file, comment_id, text=body.text, author=author)
        )

    async def post_state(thread_id: str, comment_id: str, body: DocCommentState) -> Any:
        file = _file(thread_id, body.path)
        if isinstance(file, JSONResponse):
            return file
        done = await _run(resolve_doc_comment, file, comment_id, body.resolved)
        return done if isinstance(done, JSONResponse) else {"resolved": body.resolved}

    async def remove_comment(thread_id: str, comment_id: str, path: str) -> Any:
        file = _file(thread_id, path)
        if isinstance(file, JSONResponse):
            return file
        done = await _run(delete_doc_comment, file, comment_id)
        return done if isinstance(done, JSONResponse) else {"deleted": comment_id}

    router.add_api_route(base, get_comments, methods=["GET"])
    router.add_api_route(base, post_comment, methods=["POST"])
    router.add_api_route(f"{base}/{{comment_id}}/replies", post_reply, methods=["POST"])
    router.add_api_route(f"{base}/{{comment_id}}", post_state, methods=["POST"])
    router.add_api_route(f"{base}/{{comment_id}}", remove_comment, methods=["DELETE"])


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    _read_route(router, state)
    _save_route(router, state)
    _restore_route(router, state)
    _comment_routes(router, state)
    return router
