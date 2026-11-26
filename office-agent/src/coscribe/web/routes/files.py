"""Files routes."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Form,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse, Response

from ...tools import (
    PresentationToolkit,
    WorkspaceScope,
    pdf_page_count,
    render_pdf_page,
)
from ...tools.web import SCREENSHOT_FOLDER
from ..state import AppState
from ..word_preview import add_word_preview_routes
from .shared import MAX_UPLOAD_BYTES

_PREVIEW_NAME_RE = re.compile(r"[0-9a-f]{32}\.png")  # tools/_thumbnail.py's uuid4().hex naming


_KINDS = {
    "images": frozenset(".png .jpg .jpeg .gif .webp .bmp .svg .tif .tiff .heic .ico".split()),
    "documents": frozenset(
        ".pdf .doc .docx .odt .rtf .txt .md .ppt .pptx .odp .key .pages .htm .html .epub .eml "
        ".msg".split()
    ),
    "data": frozenset(
        ".xls .xlsx .xlsm .ods .csv .tsv .json .jsonl .xml .yaml .yml .parquet .sqlite .db".split()
    ),
}


def _upload_folder(filename: str, *, pasted: bool) -> str:
    """Where in `.coscribe/uploads/` a file goes (decision 0044): by its extension, so the same
    file always lands in the same place, never by what a model makes of it."""
    if pasted:
        return "screenshots"
    suffix = Path(filename).suffix.lower()
    return next((kind for kind, suffixes in _KINDS.items() if suffix in suffixes), "other")


def _unique_upload_path(folder: Path, filename: str) -> Path:
    # A name never changes once the model has the path, so a second file with it gets a new one.
    candidate = folder / filename
    stem, suffix, counter = candidate.stem, candidate.suffix, 1
    while candidate.exists():
        candidate = folder / f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate


def _upload_name(filename: str, *, pasted: bool) -> str:
    if pasted:
        suffix = Path(filename).suffix.lower() or ".png"
        return f"screenshot-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}{suffix}"
    name = Path(filename).name
    return name if name not in {"", ".", ".."} else "upload"


def _save_upload(root: Path, filename: str, content: bytes, *, pasted: bool) -> Path:
    folder = root / ".coscribe" / "uploads" / _upload_folder(filename, pasted=pasted)
    folder.mkdir(parents=True, exist_ok=True)
    path = _unique_upload_path(folder, _upload_name(filename, pasted=pasted))
    path.write_bytes(content)
    return path


def _png_in(folder: Path, name: str) -> Response:
    path = folder / name
    if not _PREVIEW_NAME_RE.fullmatch(name) or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="image/png")


async def _spreadsheet_response(
    scope: WorkspaceScope, path: str, sheet: str | None
) -> JSONResponse:
    """Read one worksheet without evaluating formulas or updating the workbook."""
    from zipfile import BadZipFile

    from openpyxl.utils.exceptions import InvalidFileException

    from ..spreadsheet_preview import WorkbookTooLarge, read_spreadsheet

    try:
        found = scope.resolve(path)
        if found.suffix.lower() != ".xlsx" or not found.is_file():
            return JSONResponse({"error": "This workbook could not be found."}, status_code=404)
        preview = await asyncio.to_thread(read_spreadsheet, found, sheet)
    except PermissionError:
        return JSONResponse({"error": "This workbook cannot be accessed."}, status_code=403)
    except WorkbookTooLarge:
        return JSONResponse(
            {"error": "This workbook is too large to preview here."}, status_code=413
        )
    except (
        BadZipFile,
        InvalidFileException,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        OSError,
        SyntaxError,
    ):
        return JSONResponse({"error": "This workbook could not be opened."}, status_code=422)
    return JSONResponse(preview, headers={"Cache-Control": "no-store"})


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _get_session = state.get_session

    def _scope(thread_id: str) -> WorkspaceScope:
        if thread_id:
            return _get_session(thread_id).workspace_scope()
        return WorkspaceScope(settings.workspace_root)

    add_word_preview_routes(router, _scope, settings.state_dir)

    @router.post("/api/upload")
    async def upload_file(
        file: UploadFile,
        thread_id: Annotated[str, Form()] = "",
        pasted: Annotated[bool, Form()] = False,
    ) -> JSONResponse:
        """An attached file, or a pasted picture, saved in the conversation's folder under
        `.coscribe/uploads/<kind>/` (decision 0044); the path returned is relative to that
        folder, as the model reads it."""
        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            return JSONResponse({"error": "file too large (max 25MB)"}, status_code=413)
        scope = _scope(thread_id)
        try:
            path = _save_upload(scope.root, file.filename or "upload", content, pasted=pasted)
        except OSError:
            return JSONResponse(
                {"error": f"Couldn't save it in {scope.root}: the folder can't be written."},
                status_code=409,
            )
        return JSONResponse({"path": scope.relative(path), "bytes_written": len(content)})

    def _attachment_pdf(path: str, thread_id: str) -> Path | JSONResponse:
        scope = _scope(thread_id)
        try:
            file_path = scope.resolve(path)
        except PermissionError:
            return JSONResponse({"error": "Path is outside the workspace."}, status_code=400)
        if file_path.suffix.lower() != ".pdf" or not file_path.is_file():
            return JSONResponse({"error": "No such PDF."}, status_code=404)
        return file_path

    @router.get("/api/attachment/pdf")
    async def get_attachment_pdf_info(path: str, thread_id: str = "") -> JSONResponse:
        """How many pages an attached PDF has, for the preview dialog."""
        found = _attachment_pdf(path, thread_id)
        if isinstance(found, JSONResponse):
            return found
        try:
            return JSONResponse({"pages": await asyncio.to_thread(pdf_page_count, found)})
        except Exception:  # noqa: BLE001 -- a PDF PDFium can't open is shown as such
            return JSONResponse({"error": "This PDF can't be opened."}, status_code=422)

    async def spreadsheet(path: str, thread_id: str = "", sheet: str | None = None) -> JSONResponse:
        return await _spreadsheet_response(_scope(thread_id), path, sheet)

    router.add_api_route("/api/attachment/xlsx", spreadsheet, methods=["POST"])

    @router.get("/api/attachment/pdf/page")
    async def get_attachment_pdf_page(
        path: str, page: int = 1, width: int = 600, thread_id: str = ""
    ) -> Response:
        found = _attachment_pdf(path, thread_id)
        if isinstance(found, JSONResponse):
            return found
        try:
            png = await asyncio.to_thread(render_pdf_page, found, page, width)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        except Exception:  # noqa: BLE001 -- see above
            return JSONResponse({"error": "This PDF can't be opened."}, status_code=422)
        return Response(png, media_type="image/png", headers={"Cache-Control": "max-age=3600"})

    @router.get("/api/previews/{name}")
    async def get_preview(name: str) -> Response:
        # Serves the write_docx/write_xlsx/write_pptx thumbnails written by
        # tools/_thumbnail.py's render_thumbnail under
        # settings.state_dir/previews/ -- not a general file-access endpoint
        # (unlike a WorkspaceScope-backed route, there's no user-supplied
        # path to sanitize against traversal here: `name` is checked against
        # the exact `<32 hex chars>.png` shape render_thumbnail always
        # generates, so it can only ever resolve to a plain filename inside
        # that one directory).
        return _png_in(settings.state_dir / "previews", name)

    @router.get("/api/screenshots/{name}")
    async def get_screenshot(name: str) -> Response:
        # Same shape check as previews: only a page_screenshot file name.
        return _png_in(settings.state_dir / SCREENSHOT_FOLDER, name)

    @router.get("/api/pptx-shapes")
    async def get_pptx_shapes(path: str, slide: int, thread_id: str = "") -> JSONResponse:
        # Backs the click-a-shape-in-the-preview-to-target-it feature
        # (ChatLog.tsx's PptxShapeOverlay): the frontend already has
        # `path` from the tool call's own `arguments.path` and picks
        # `slide` from `arguments.slide` (edits) or defaults to 1 (a
        # fresh write_pptx), then overlays clickable regions on top of
        # the already-rendered preview image using this endpoint's
        # inch-based bboxes (converted to on-screen percentages -- see
        # PresentationToolkit.list_pptx_shapes's own docstring for why
        # inches, not pixels). Same underlying method the LLM-facing
        # list_pptx_shapes tool calls -- this is a plain, ungated REST
        # read, not a tool call, since it's UI-only (never reaches the
        # model, never touches the audit log a real tool call would).
        scope = _scope(thread_id)
        toolkit = PresentationToolkit(
            scope.root,
            state_dir=settings.state_dir,
            extra_readable=scope.extra_readable,
            extra_writable=scope.extra_writable,
        )
        try:
            result = await asyncio.to_thread(toolkit.list_pptx_shapes, path=path, slide=slide)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(result)

    @router.get("/api/browse-dirs")
    async def browse_dirs(path: str | None = None) -> dict[str, Any]:
        # Direct port of the old hand-rolled runtime's identical endpoint
        # (deleted in the web cutover, see runtime_lg/README.md) -- missing
        # here entirely was a real live-reported bug: app.js (shared by
        # both backends while they coexisted) drives this folder-browser
        # modal for the Settings panel's extra_readable_dirs/
        # extra_writable_dirs picker, but this app didn't define the route
        # yet at the time, so the fetch 404'd and the modal opened empty/
        # broken with no error surfaced. Same deliberately-unrestricted
        # trust model as before: no auth, local-only, and the user could
        # already type any absolute path into that field by hand.
        target = Path(path).expanduser() if path else Path.home()
        try:
            resolved = target.resolve()
        except OSError as exc:
            return {"error": str(exc)}
        if not resolved.is_dir():
            return {"error": f"Not a directory: {resolved}"}
        directories = []
        try:
            for entry in resolved.iterdir():
                try:
                    if entry.is_dir():
                        directories.append({"name": entry.name, "path": str(entry)})
                except OSError:
                    continue  # unreadable entry (permissions, broken link, ...) -- skip it
        except OSError as exc:
            return {"error": str(exc)}
        return {
            "path": str(resolved),
            "parent": str(resolved.parent) if resolved.parent != resolved else None,
            "directories": sorted(directories, key=lambda d: d["name"].lower()),
        }

    return router
