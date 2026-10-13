"""Page text of a PDF, via pdfium."""

from __future__ import annotations

import threading
from pathlib import Path

_PDFIUM_LOCK = threading.Lock()


def _pdf_page_texts(
    file_path: Path, start_page: int = 1, end_page: int = 0
) -> list[tuple[int, str]]:
    """(1-based page number, text) pairs, via pdfium rather than
    pdfplumber: ~100x faster (650 pages in ~1.6s vs ~130s measured), and
    pdfplumber's pure-Python parsing holds the GIL for that whole time,
    stalling the web server's event loop along with it. PDFium itself is
    not thread-safe, hence the lock -- tool calls can run concurrently."""
    import pypdfium2 as pdfium

    pages: list[tuple[int, str]] = []
    with _PDFIUM_LOCK:
        document = pdfium.PdfDocument(str(file_path))
        try:
            last = len(document) if end_page <= 0 else min(end_page, len(document))
            for index in range(max(start_page, 1), last + 1):
                page = document[index - 1]
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range()
                finally:
                    textpage.close()
                    page.close()
                pages.append((index, text.replace("\r\n", "\n")))
        finally:
            document.close()
    return pages
