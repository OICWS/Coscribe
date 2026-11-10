"""The Files panel's routes: a conversation's folders listed one level at a time, searched by
name, and a file served as it is. Read only; nothing here writes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse, Response

from ..state import AppState

# Never worth showing: git's own store and the lock files Office leaves beside an open document.
_HIDDEN = frozenset({".git", "desktop.ini", "Thumbs.db", ".DS_Store"})
# Shown, but greyed out and never searched: a search through them would take the whole budget.
_HEAVY = frozenset({"node_modules", "__pycache__", ".venv", "venv", ".tox"})
_MAX_ENTRIES = 2000
_SEARCH_VISITS = 20_000
_SEARCH_RESULTS = 200
# A page served from the user's folder is shown, never run: the panel's frame has no scripts and
# this keeps it so when the file is opened on its own. Same-origin stays allowed so its pictures
# and styles load (a sandboxed frame without it is refused by the cross-site GET guard).
_RAW_HEADERS = {
    "Content-Security-Policy": "script-src 'none'; object-src 'none'; frame-ancestors 'self'",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}
_PDF_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"}


def _hidden(name: str) -> bool:
    return name in _HIDDEN or name.startswith("~$")


def _heavy(name: str) -> bool:
    return name in _HEAVY or name.endswith("_cache")


def _entry(item: os.DirEntry[str]) -> dict[str, Any] | None:
    try:
        is_dir = item.is_dir()
        size = None if is_dir else item.stat().st_size
    except OSError:
        return None
    entry: dict[str, Any] = {"name": item.name, "dir": is_dir, "size": size}
    if is_dir and _heavy(item.name):
        entry["dim"] = True
    return entry


def list_folder(folder: Path) -> dict[str, Any]:
    """One level of a folder: its `.coscribe` first, then folders, then files, each by name
    ignoring case."""
    with os.scandir(folder) as items:
        entries = [e for item in items if not _hidden(item.name) and (e := _entry(item))]
    entries.sort(key=lambda e: (e["name"] != ".coscribe", not e["dir"], e["name"].casefold()))
    return {"entries": entries[:_MAX_ENTRIES], "truncated": len(entries) > _MAX_ENTRIES}


def find_files(root: Path, query: str) -> dict[str, Any]:
    """Files and folders whose name holds `query`, as paths under `root`, breadth first so the
    shallow ones come before a deep tree uses up the budget."""
    needle = query.casefold()
    found: list[dict[str, Any]] = []
    queue, visits = [root], 0
    while queue and visits < _SEARCH_VISITS and len(found) < _SEARCH_RESULTS:
        folder = queue.pop(0)
        try:
            items = sorted(os.scandir(folder), key=lambda i: i.name.casefold())
        except OSError:
            continue
        for item in items:
            visits += 1
            if _hidden(item.name):
                continue
            entry = _entry(item)
            if entry is None:
                continue
            if needle in item.name.casefold():
                found.append({**entry, "path": Path(item.path).relative_to(root).as_posix()})
            if entry["dir"] and not _heavy(item.name) and not item.is_symlink():
                queue.append(Path(item.path))
    return {"entries": found[:_SEARCH_RESULTS], "truncated": bool(queue)}


def _inside(root: Path, path: str) -> Path | None:
    """`path` under `root`, or None for one that leaves it (`..`, an absolute path, a link out)."""
    if Path(path).is_absolute():
        return None
    resolved = (root / path).resolve()
    return resolved if resolved == root or resolved.is_relative_to(root) else None


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    def folders(thread_id: str) -> list[Path]:
        session = state.get_session(thread_id)
        return [
            Path(session.workspace_root).resolve(),
            *(Path(f).resolve() for f in session.extra_folders),
        ]

    def root_of(thread_id: str, root: int) -> Path | None:
        roots = folders(thread_id)
        return roots[root] if 0 <= root < len(roots) else None

    async def get_roots(thread_id: str) -> dict[str, Any]:
        return {"roots": [{"name": f.name or str(f), "path": str(f)} for f in folders(thread_id)]}

    async def get_listing(thread_id: str, root: int, path: str = "") -> Response | dict[str, Any]:
        base = root_of(thread_id, root)
        folder = _inside(base, path) if base else None
        if folder is None or not folder.is_dir():
            return JSONResponse({"error": f"No folder {path!r}"}, status_code=404)
        try:
            return list_folder(folder)
        except OSError as exc:
            return JSONResponse({"error": f"Couldn't read it: {exc.strerror}"}, status_code=403)

    async def get_search(thread_id: str, root: int, q: str) -> Response | dict[str, Any]:
        base = root_of(thread_id, root)
        if base is None:
            return JSONResponse({"error": "No such folder"}, status_code=404)
        return find_files(base, q) if q.strip() else {"entries": [], "truncated": False}

    async def get_raw(thread_id: str, root: int, path: str) -> Response:
        base = root_of(thread_id, root)
        file = _inside(base, path) if base else None
        if file is None or not file.is_file():
            return JSONResponse({"error": f"No file {path!r}"}, status_code=404)
        # A PDF keeps the browser's own viewer, which a CSP without plugins would refuse.
        headers = _RAW_HEADERS if file.suffix.lower() != ".pdf" else _PDF_HEADERS
        return FileResponse(file, headers=headers, content_disposition_type="inline")

    prefix = "/api/threads/{thread_id}/workspace"
    router.add_api_route(prefix, get_roots, methods=["GET"])
    router.add_api_route(
        f"{prefix}/{{root}}/list", get_listing, methods=["GET"], response_model=None
    )
    router.add_api_route(
        f"{prefix}/{{root}}/search", get_search, methods=["GET"], response_model=None
    )
    router.add_api_route(f"{prefix}/{{root}}/raw/{{path:path}}", get_raw, methods=["GET"])
    return router
