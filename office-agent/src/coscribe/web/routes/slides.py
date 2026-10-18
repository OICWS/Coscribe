"""The Slides panel's reads: a deck built from pages, one slide of it as an SVG (decision 0016),
and its downloads. Read only; the panel's edits come with the section editor."""

from __future__ import annotations

import asyncio
import getpass
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from ...tools import (
    CommentNotFound,
    NotBuiltFromPages,
    add_comment,
    deck_basic_fonts,
    deck_html,
    deck_pdf,
    delete_comment,
    read_comments,
    read_deck,
    reply_to_comment,
    resolve_comment,
    slide_svg,
)
from ..schemas import SlideCommentNew, SlideCommentReply, SlideCommentState
from ..state import AppState

# The SVG is drawn by the panel as an image, which runs nothing; this keeps it inert too when
# it is opened on its own, since it is served from the app's origin.
_SVG_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; img-src data:; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}

# Fixed messages: a parser's own text can carry paths and internals, and the panel only needs to
# say what to do.
_NOT_BUILT = "This presentation was not built from slide pages"
_UNREADABLE = "This presentation or one of its pages could not be read"


_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
# Each download: its file-name ending, its type, and how it is made from the deck and workspace.
_EXPORTS: dict[str, tuple[str, str, Callable[[Path, Path], bytes | str]]] = {
    "pdf": (".pdf", "application/pdf", deck_pdf),
    "html": (".html", "text/html; charset=utf-8", deck_html),
    "pptx-basic": (" (basic fonts).pptx", _PPTX, lambda deck, _workspace: deck_basic_fonts(deck)),
}


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    async def get_slides(thread_id: str, path: str) -> Any:
        found = _deck_file(state, thread_id, path)
        if found is None:
            return _no_deck(path)
        return await _run(read_deck, found[0])

    async def get_slide_svg(thread_id: str, index: int, path: str) -> Response:
        found = _deck_file(state, thread_id, path)
        if found is None:
            return _no_deck(path)
        svg = await _run(slide_svg, found[0], index, found[1])
        if isinstance(svg, Response):
            return svg
        return Response(svg, media_type="image/svg+xml", headers=_SVG_HEADERS)

    async def export_slides(thread_id: str, path: str, format: str) -> Response:
        found = _deck_file(state, thread_id, path)
        if found is None:
            return _no_deck(path)
        if format not in _EXPORTS:
            return JSONResponse({"error": f"No export {format!r}"}, status_code=400)
        suffix, media_type, export = _EXPORTS[format]
        data = await _run(export, *found)
        if isinstance(data, Response):
            return data
        name = f"{found[0].stem}{suffix}"
        return Response(
            data,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
        )

    _comment_routes(router, state)
    router.add_api_route("/api/threads/{thread_id}/slides", get_slides, methods=["GET"])
    router.add_api_route("/api/threads/{thread_id}/slides/export", export_slides, methods=["GET"])
    router.add_api_route(
        "/api/threads/{thread_id}/slides/{index}/svg", get_slide_svg, methods=["GET"]
    )
    return router


def _comment_routes(router: APIRouter, state: AppState) -> None:
    """The deck's comments: read them, add one, reply, resolve or reopen, delete."""
    base = "/api/threads/{thread_id}/slides/comments"

    async def get_comments(thread_id: str, path: str) -> Any:
        found = _deck_file(state, thread_id, path)
        return _no_deck(path) if found is None else await _run(read_comments, found[0])

    async def post_comment(thread_id: str, body: SlideCommentNew) -> Any:
        found = _deck_file(state, thread_id, body.path)
        if found is None:
            return _no_deck(body.path)
        fields = body.model_dump(exclude={"path"})
        return await _run(lambda: add_comment(found[0], author=_author(), **fields))

    async def post_reply(thread_id: str, comment_id: str, body: SlideCommentReply) -> Any:
        found = _deck_file(state, thread_id, body.path)
        if found is None:
            return _no_deck(body.path)
        author = "coscribe" if body.from_coscribe else _author()
        return await _run(
            lambda: reply_to_comment(found[0], comment_id, text=body.text, author=author)
        )

    async def post_state(thread_id: str, comment_id: str, body: SlideCommentState) -> Any:
        found = _deck_file(state, thread_id, body.path)
        if found is None:
            return _no_deck(body.path)
        done = await _run(resolve_comment, found[0], comment_id, body.resolved)
        return done if isinstance(done, Response) else {"resolved": body.resolved}

    async def remove_comment(thread_id: str, comment_id: str, path: str) -> Any:
        found = _deck_file(state, thread_id, path)
        if found is None:
            return _no_deck(path)
        done = await _run(delete_comment, found[0], comment_id)
        return done if isinstance(done, Response) else {"deleted": comment_id}

    router.add_api_route(base, get_comments, methods=["GET"])
    router.add_api_route(base, post_comment, methods=["POST"])
    router.add_api_route(f"{base}/{{comment_id}}/replies", post_reply, methods=["POST"])
    router.add_api_route(f"{base}/{{comment_id}}", post_state, methods=["POST"])
    router.add_api_route(f"{base}/{{comment_id}}", remove_comment, methods=["DELETE"])


def _author() -> str:
    # Word names a reviewer after the computer's user until one is set; comments do the same.
    return getpass.getuser()


def _deck_file(state: AppState, thread_id: str, path: str) -> tuple[Path, Path] | None:
    """The deck and the workspace it may draw pictures from, when `path` is a .pptx there."""
    try:
        scope = state.get_session(thread_id).workspace_scope()
        deck = scope.resolve(path)
    except (PermissionError, OSError, ValueError):
        return None
    if not deck.is_file() or deck.suffix.lower() != ".pptx":
        return None
    return deck, Path(scope.root)


def _no_deck(path: str) -> JSONResponse:
    return JSONResponse({"error": f"No deck {path!r}"}, status_code=404)


async def _run(job: Callable[..., Any], *args: Any) -> Any:
    """`job` off the event loop, or the response its failure gets."""
    try:
        return await asyncio.to_thread(job, *args)
    except CommentNotFound:
        return JSONResponse({"error": "No such comment"}, status_code=404)
    except IndexError:
        return JSONResponse({"error": "No such slide"}, status_code=404)
    except NotBuiltFromPages:
        return JSONResponse({"error": _NOT_BUILT, "built": False}, status_code=409)
    except (ValueError, SyntaxError, zipfile.BadZipFile):
        return JSONResponse({"error": _UNREADABLE}, status_code=400)
