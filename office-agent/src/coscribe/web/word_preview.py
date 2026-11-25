"""Read-only Word previews produced by the same local engines as file conversion."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from ..tools import WorkspaceScope, build_convert_tools

_MAX_DOCX_BYTES = 50 * 1024 * 1024
_MAX_PDF_BYTES = 32 * 1024 * 1024
_MAX_CACHE_BYTES = 48 * 1024 * 1024
_WORD_DOCUMENT_TYPE = (
    b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)


def word_preview_version(path: Path) -> str:
    stat = path.stat()
    if stat.st_size > _MAX_DOCX_BYTES:
        raise ValueError("This document is too large to preview. Open it in its own app.")
    return f'"{stat.st_size:x}-{stat.st_mtime_ns:x}-{stat.st_ctime_ns:x}-{stat.st_ino:x}"'


def _check_document(path: Path) -> None:
    # An Office file renamed to DOCX must not reach the preview engine as a macro-enabled file.
    try:
        with ZipFile(path) as archive:
            types = archive.getinfo("[Content_Types].xml")
            with archive.open(types) as content:
                manifest = content.read(512 * 1024).replace(b"\0", b"")
            if _WORD_DOCUMENT_TYPE not in manifest or b"macroEnabled" in manifest:
                raise ValueError("This file is not a standard Word DOCX document.")
            if any(part.filename.lower().endswith("vbaproject.bin") for part in archive.infolist()):
                raise ValueError("Word preview is unavailable for documents containing macros.")
    except (BadZipFile, KeyError, RuntimeError):
        raise ValueError("This Word document is damaged or password-protected.") from None


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
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            data = self._convert(source, version)
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
                raise ValueError("The document changed while the preview was starting. Try again.")
            _check_document(snapshot)
            target = folder / "preview.pdf"
            (convert,) = build_convert_tools(folder, state_dir=self._state_dir)
            convert("document.docx", "pdf", "preview.pdf")
            if target.stat().st_size > _MAX_PDF_BYTES:
                raise ValueError(
                    "The generated preview is too large to display. Open it in its own app."
                )
            return target.read_bytes()


def add_word_preview_routes(
    router: APIRouter, _scope: Callable[[str], WorkspaceScope], state_dir: Path
) -> None:
    word_previews = WordPreviews(state_dir)

    @router.get("/api/attachment/docx", response_class=Response)
    async def get_word_preview(request: Request, path: str, thread_id: str) -> Response:
        try:
            file_path = _scope(thread_id).resolve(path)
            if file_path.suffix.lower() != ".docx" or not file_path.is_file():
                return JSONResponse({"error": "No such Word document."}, status_code=404)
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
        except (OSError, ValueError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)

    router.add_api_route(
        "/api/attachment/docx", get_word_preview, methods=["HEAD"], include_in_schema=False
    )
