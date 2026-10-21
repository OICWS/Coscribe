"""A .pptx coscribe did not build, drawn read-only for the Slides panel.

Its slides are not pages coscribe can draw, so the installed office program (Microsoft Office or
WPS, decision 0012) writes the deck as a PDF, once per version of the file, and each slide is that
PDF's page, drawn by PDFium and held in an SVG as a picture. Without a program there is nothing to
show, and the panel says it was not built by coscribe, as before.
"""

from __future__ import annotations

import base64
import hashlib
import io
import threading
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from pptx import Presentation

from ...._office_com import convert
from .view import NotBuiltFromPages, _notes, _transition, slide_elements

_OFFICE_TIMEOUT = 60.0
_WIDTH = 1280
_RENDER_SCALE = 2.0
# The panel asks for every thumbnail at once; the first one makes the PDF and the rest wait for it.
_PDF_LOCK = threading.Lock()


def _pdf(deck: Path, state_dir: Path) -> Path:
    """The deck's PDF under `state_dir`, made once for this version of the file."""
    stat = deck.stat()
    key = hashlib.sha256(f"{deck.resolve()}:{stat.st_mtime_ns}:{stat.st_size}".encode()).hexdigest()
    target = state_dir / "foreign-decks" / f"{key[:32]}.pdf"
    with _PDF_LOCK:
        if target.is_file():
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            written = convert(deck, target, "pdf", _OFFICE_TIMEOUT)
        except ValueError as error:
            raise NotBuiltFromPages(str(error)) from None
        if written is None or not target.is_file():
            raise NotBuiltFromPages(
                f"{deck.name} was not built from pages and cannot be drawn here"
            )
    return target


def foreign_deck(deck: Path, state_dir: Path) -> dict[str, Any]:
    """What `read_deck` returns for a deck coscribe built, for one it did not: read-only."""
    _pdf(deck, state_dir)
    prs = Presentation(str(deck))
    width, height = prs.slide_width or 1, prs.slide_height or 1
    slides = [
        {
            "name": f"slide {number}",
            "kind": "page",
            "notes": _notes(slide),
            "transition": _transition(slide),
            "background": None,
            "elements": slide_elements(slide, width, height),
        }
        for number, slide in enumerate(prs.slides, start=1)
    ]
    return {
        "title": deck.stem,
        "folder": "",
        "changed": False,
        "readOnly": True,
        "slides": slides,
    }


def foreign_slide_svg(deck: Path, index: int, state_dir: Path) -> str:
    """Slide `index` (from 0) as an SVG holding its picture. Raises IndexError for no such slide."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(_pdf(deck, state_dir)))
    try:
        if not 0 <= index < len(document):
            raise IndexError(f"no slide {index + 1}")
        page = document[index]
        page_width, page_height = page.get_size()
        image = page.render(scale=_RENDER_SCALE).to_pil()
    finally:
        document.close()
    height = round(_WIDTH * page_height / page_width)
    png = io.BytesIO()
    image.save(png, format="PNG")
    data = base64.b64encode(png.getvalue()).decode()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_WIDTH} {height}" '
        f'width="{_WIDTH}" height="{height}">'
        f'<image width="{_WIDTH}" height="{height}" href="data:image/png;base64,{escape(data)}"/>'
        "</svg>"
    )
