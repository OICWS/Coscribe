"""PDF read, search and write tools, scoped to a single workspace root.

Text comes from `pypdfium2` (see `text._pdf_page_texts` for why not `pdfplumber`); `write_pdf`
uses the same markdown subset as `write_docx` and renders it with `reportlab`, imported
lazily like every other heavy library here."""

from __future__ import annotations

from .text import _PDFIUM_LOCK as PDFIUM_LOCK
from .toolkit import PdfToolkit
from .tools import build_pdf_tools

__all__ = ["PDFIUM_LOCK", "PdfToolkit", "build_pdf_tools"]
