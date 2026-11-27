"""Read-only Word previews produced by the same local engines as file conversion."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from collections import OrderedDict
from collections.abc import AsyncIterator, Callable
from enum import Enum
from pathlib import Path
from threading import Lock
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from watchfiles import awatch

from ..tools import WorkspaceScope, build_convert_tools

_MAX_DOCX_BYTES = 50 * 1024 * 1024
_MAX_PDF_BYTES = 32 * 1024 * 1024
_MAX_CACHE_BYTES = 48 * 1024 * 1024
_WORD_DOCUMENT_TYPE = (
    b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)
logger = logging.getLogger(__name__)


class _PreviewProblem(Enum):
    TOO_LARGE = "This document is too large to preview. Open it in its own app."
    INVALID = "This file is not a standard Word DOCX document."
    MACROS = "Word preview is unavailable for documents containing macros."
    DAMAGED = "This Word document is damaged or password-protected."
    CHANGED = "The document changed while the preview was starting. Try again."
    OUTPUT_TOO_LARGE = "The generated preview is too large to display. Open it in its own app."
    CONVERSION_FAILED = (
        "Couldn't prepare a Word preview. Check that Word, WPS, or LibreOffice is available, "
        "or open the original."
    )


class _WordPreviewError(ValueError):
    def __init__(self, problem: _PreviewProblem) -> None:
        super().__init__(problem.value)
        self.problem = problem


def word_preview_version(path: Path) -> str:
    stat = path.stat()
    return f'"{stat.st_size:x}-{stat.st_mtime_ns:x}-{stat.st_ctime_ns:x}-{stat.st_ino:x}"'


def _check_document(path: Path) -> None:
    # An Office file renamed to DOCX must not reach the preview engine as a macro-enabled file.
    try:
        with ZipFile(path) as archive:
            types = archive.getinfo("[Content_Types].xml")
            with archive.open(types) as content:
                manifest = content.read(512 * 1024).replace(b"\0", b"")
            if _WORD_DOCUMENT_TYPE not in manifest or b"macroEnabled" in manifest:
                raise _WordPreviewError(_PreviewProblem.INVALID)
            if any(part.filename.lower().endswith("vbaproject.bin") for part in archive.infolist()):
                raise _WordPreviewError(_PreviewProblem.MACROS)
    except (BadZipFile, KeyError, RuntimeError):
        raise _WordPreviewError(_PreviewProblem.DAMAGED) from None


class WordPreviews:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._cache: OrderedDict[tuple[Path, str], bytes] = OrderedDict()
        self._lock = Lock()

    def get(self, source: Path, version: str) -> bytes:
        key = (source, version)
        # The Office worker and its app instance are shared. Concurrent clicks on the same
        # document should share the results, even if an earlier HTTP request disconnected.
        with self._lock:
            if word_preview_version(source) != version:
                raise _WordPreviewError(_PreviewProblem.CHANGED)
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            data = self._convert(source, version)
            if word_preview_version(source) != version:
                raise _WordPreviewError(_PreviewProblem.CHANGED)
            self._cache[key] = data
            while len(self._cache) > 6 or sum(map(len, self._cache.values())) > _MAX_CACHE_BYTES:
                self._cache.popitem(last=False)
            return data

    def _convert(self, source: Path, version: str) -> bytes:
        # Word can return an existing open Document object when asked to open its path again.
        # Using a separate path means the converter can only close the copy it opened.
        with tempfile.TemporaryDirectory(prefix="coscribe_word_preview_") as directory:
            folder = Path(directory)
            snapshot = folder / "document.docx"
            shutil.copyfile(source, snapshot)
            if word_preview_version(source) != version:
                raise _WordPreviewError(_PreviewProblem.CHANGED)
            _check_document(snapshot)
            target = folder / "preview.pdf"
            (convert,) = build_convert_tools(folder, state_dir=self._state_dir)
            try:
                convert("document.docx", "pdf", "preview.pdf")
                size = target.stat().st_size
            except (OSError, ValueError) as exc:
                raise _WordPreviewError(_PreviewProblem.CONVERSION_FAILED) from exc
            if size > _MAX_PDF_BYTES:
                raise _WordPreviewError(_PreviewProblem.OUTPUT_TOO_LARGE)
            return target.read_bytes()


def _source(scope: WorkspaceScope, path: str) -> Path:
    file = scope.resolve(path)
    if file.suffix.lower() != ".docx" or not file.is_file():
        raise FileNotFoundError
    return file


async def _word_versions(source: Path, current: Callable[[], Path]) -> AsyncIterator[str]:
    # Office commonly saves by replacing the source. Watch its directory, not its old inode.
    previous: str | None = ""
    try:
        async for _ in awatch(
            source.parent,
            recursive=False,
            debounce=180,
            step=55,
            rust_timeout=2000,
            yield_on_timeout=True,
            watch_filter=lambda _, name: Path(name) == source,
        ):
            try:
                version = await asyncio.to_thread(lambda: word_preview_version(current()))
            except (OSError, ValueError):
                version = None
            if version != previous:
                previous = version
                yield f"data: {json.dumps(version)}\n\n"
            else:
                yield ": heartbeat\n\n"
    except OSError:
        # The directory may itself have been removed. EventSource can reconnect.
        return


def add_word_preview_routes(
    router: APIRouter, _scope: Callable[[str], WorkspaceScope], state_dir: Path
) -> None:
    word_previews = WordPreviews(state_dir)

    async def word_versions(path: str, thread_id: str) -> Response:
        def current() -> Path:
            return _source(_scope(thread_id), path)

        try:
            source = _scope(thread_id).resolve(path)
            if source.suffix.lower() != ".docx" or not source.parent.is_dir():
                return Response(status_code=404)
        except PermissionError:
            return Response(status_code=403)
        except (OSError, ValueError):
            return Response(status_code=404)
        return StreamingResponse(
            _word_versions(source, current),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store"},
        )

    router.add_api_route(
        "/api/attachment/docx/versions",
        word_versions,
        methods=["GET"],
        response_class=StreamingResponse,
    )

    @router.post("/api/attachment/docx", response_class=Response)
    async def get_word_preview(request: Request, path: str, thread_id: str) -> Response:
        try:
            file_path = _source(_scope(thread_id), path)
            if file_path.stat().st_size > _MAX_DOCX_BYTES:
                raise _WordPreviewError(_PreviewProblem.TOO_LARGE)
            version = word_preview_version(file_path)
            headers = {"ETag": version, "Cache-Control": "no-store"}
            if request.method == "HEAD":
                return Response(headers=headers)
            pdf = await asyncio.to_thread(word_previews.get, file_path, version)
            return Response(pdf, media_type="application/pdf", headers=headers)
        except PermissionError:
            return JSONResponse(
                {"error": "This document cannot be opened from this conversation."}, status_code=403
            )
        except FileNotFoundError:
            return JSONResponse({"error": "No such Word document."}, status_code=404)
        except _WordPreviewError as exc:
            if exc.problem is _PreviewProblem.CHANGED:
                return JSONResponse({"error": exc.problem.value}, status_code=409)
            if exc.problem is _PreviewProblem.CONVERSION_FAILED:
                logger.warning("Word preview conversion failed", exc_info=True)
            return JSONResponse({"error": exc.problem.value}, status_code=422)
        except (OSError, ValueError):
            logger.warning("Word preview could not read the document", exc_info=True)
            return JSONResponse(
                {"error": "Couldn't read the Word document for preview."}, status_code=422
            )

    # HEAD exposes the source version only. Preview generation uses the launch-token-guarded POST.
    router.add_api_route(
        "/api/attachment/docx", get_word_preview, methods=["HEAD"], include_in_schema=False
    )
