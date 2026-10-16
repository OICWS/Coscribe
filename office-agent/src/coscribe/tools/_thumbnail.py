"""Page previews of an office file, shared by the write tools, `preview_pptx`, `review_work`
and the approval card's slide preview (conversation/edit_preview.py).

No office program is needed for a PDF (PDFium) or for a deck still as its SVG pages built it
(resvg); any other Word, Excel or PowerPoint file is drawn through the office program installed,
Microsoft Office or WPS, over COM (decision 0012). Without one there is no preview, and the
reason says so: a preview is never an error, since the write has already succeeded.

Previews are written under `<state_dir>/previews/`, not the user's workspace. Their names are
fresh uuid4s, never derived from the source path, so `GET /api/previews/{name}` looks one up by
a plain name match in that one directory without path-traversal checks.
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from . import _office_com

# The first start of Word or PowerPoint after a login can take half a minute.
OFFICE_TIMEOUT = 60.0
NO_OFFICE_PROGRAM = "drawing this file needs Microsoft Office or WPS Office, and neither was found"

_PREVIEW_DPI = 100
# What drawing a page raises: resvg's ValueError, a malformed SVG, PDFium's RuntimeError, a file
# that went away, the office program failing (ValueError). A preview is never worth failing the
# write.
_DRAW_ERRORS = (ValueError, SyntaxError, RuntimeError, OSError)


def _draw(
    file_path: Path,
    out_dir: Path,
    first: int,
    last: int,
    layout: list[dict[str, Any]] | None = None,
) -> list[Path] | None:
    """Pages first..last as PNG files: a PDF with PDFium; a deck its SVG pages last built, deck
    and pages still as built, with resvg; any other Office file through the office program
    installed, its PDF then drawn by PDFium, with the words of its pages added to `layout`.
    None when no office program can draw it. Raises one of `_DRAW_ERRORS` on a failure."""
    if file_path.suffix.lower() == ".pdf":
        return _render_pdf_pages(file_path, out_dir, first, last)
    pages = _built_pages(file_path)
    if pages is None:
        pdf_path = out_dir / f"{file_path.stem}.pdf"
        if _office_com.convert(file_path, pdf_path, "pdf", OFFICE_TIMEOUT) is None:
            return None
        if layout is not None:
            layout.extend(measure_page_words(pdf_path, last))
        return _render_pdf_pages(pdf_path, out_dir, first, last)
    from ._svg_preview import render_page

    files = []
    for number, page in enumerate(pages[max(first, 1) - 1 : last], max(first, 1)):
        target = out_dir / f"page-{number:04d}.png"
        render_page(page, target)
        files.append(target)
    return files


def _built_pages(file_path: Path) -> list[Path] | None:
    if file_path.suffix.lower() != ".pptx":
        return None
    from .office.pptx.engine.build import built_pages

    return built_pages(file_path)


def _keep(page_files: list[Path], state_dir: Path) -> list[str]:
    previews_dir = state_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    names = []
    for page_file in page_files:
        name = f"{uuid.uuid4().hex}.png"
        shutil.move(str(page_file), str(previews_dir / name))
        names.append(name)
    return names


def _previews(
    file_path: Path,
    state_dir: Path | None,
    first: int,
    last: int,
    layout: list[dict[str, Any]] | None = None,
) -> tuple[list[str], str | None]:
    if state_dir is None:
        return [], "no state_dir configured"
    out_dir = Path(tempfile.mkdtemp(prefix="coscribe_thumbnail_"))
    try:
        try:
            page_files = _draw(file_path, out_dir, first, last, layout)
        except _DRAW_ERRORS:
            return [], "page rendering failed"
        if page_files is None:
            return [], NO_OFFICE_PROGRAM
        if not page_files:
            return [], (
                f"page {first} out of range for this document"
                if first > 1
                else "no pages to render"
            )
        return _keep(page_files, state_dir), None
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def render_thumbnail(file_path: Path, state_dir: Path | None) -> tuple[str | None, str | None]:
    """The first page of `file_path` (docx/pdf/xlsx/pptx) as a PNG under `state_dir/previews/`:
    `(preview_name, None)`, the name a bare file name for `GET /api/previews/{name}`, or
    `(None, reason)`. Never raises."""
    names, reason = _previews(file_path, state_dir, 1, 1)
    return (names[0] if names else None), reason


def measure_page_words(pdf_path: Path, max_pages: int) -> list[dict[str, Any]]:
    """Per page: {"width", "height", "words": [(x0, y0, x1, y1)]} in points
    with y measured down from the top, from PDFium's character boxes -- where
    the text really landed once rendered, which the file alone can't say
    (inherited sizes, autofit). The loose box is the font's own ascent to
    descent, about 1.2x the size, the same box poppler's word boxes gave.
    Empty on any failure: a measurement is never worth failing a preview."""
    try:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(str(pdf_path))
    except Exception:  # noqa: BLE001 -- see docstring
        return []
    pages: list[dict[str, Any]] = []
    try:
        for index in range(min(max_pages, len(document))):
            page = document[index]
            width, height = page.get_size()
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            words: list[tuple[float, float, float, float]] = []
            current: list[float] | None = None
            for position, char in enumerate(text):
                if char.isspace() or char in "\x02\ufffe":
                    if current is not None:
                        words.append((current[0], current[1], current[2], current[3]))
                        current = None
                    continue
                left, bottom, right, top = textpage.get_charbox(position, loose=True)
                box = [left, height - top, right, height - bottom]
                if current is None:
                    current = box
                else:
                    current = [
                        min(current[0], box[0]),
                        min(current[1], box[1]),
                        max(current[2], box[2]),
                        max(current[3], box[3]),
                    ]
            if current is not None:
                words.append((current[0], current[1], current[2], current[3]))
            pages.append({"width": float(width), "height": float(height), "words": words})
    except Exception:  # noqa: BLE001 -- see docstring
        return []
    finally:
        document.close()
    return pages


def _render_pdf_pages(pdf_path: Path, out_dir: Path, first: int, last: int) -> list[Path]:
    """PNG files for pages first..last (1-based, clipped to the document).
    PDFium renders them, so nothing outside Python is needed -- poppler is
    not something a Windows machine has."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    files: list[Path] = []
    try:
        for number in range(max(first, 1), min(last, len(document)) + 1):
            image = document[number - 1].render(scale=_PREVIEW_DPI / 72).to_pil()
            target = out_dir / f"page-{number:04d}.png"
            image.save(target)
            files.append(target)
    finally:
        document.close()
    return files


def render_all_page_previews(
    file_path: Path,
    state_dir: Path | None,
    max_pages: int = 8,
    layout: list[dict[str, Any]] | None = None,
) -> tuple[list[str], str | None]:
    """Every page of `file_path` up to `max_pages`, each its own PNG: a first-page check missed a
    deck whose title slide looked fine and whose other slides were plain bullet lists. A large
    deck's every slide is not worth the tokens of reviewing each. `layout` receives the words of
    each page when the file was drawn through its PDF. `([], reason)` when skipped; never
    raises."""
    return _previews(file_path, state_dir, 1, max_pages, layout)


def render_single_page_preview(
    file_path: Path, state_dir: Path | None, page: int
) -> tuple[str | None, str | None]:
    """Page `page` (1-based) alone, for the approval card's preview of the one slide an edit
    targets, without drawing the pages before it as images. `(None, reason)` on any failure,
    a page out of range included; never raises."""
    names, reason = _previews(file_path, state_dir, page, page)
    return (names[0] if names else None), reason
