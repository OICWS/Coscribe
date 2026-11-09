"""What a generated document's pages look like once an office program has laid them out (decision
0026): an empty page, text that runs past the paper's edge (a table too wide), and a last page that
holds only a line or two. The file alone can't say any of this; only the PDF the program made can.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._pdfium import PDFIUM_LOCK

# A character this far past the paper (in points) has left it; nearer is rounding.
_EDGE_PT = 1.0
# A last page with fewer letters than this is a line or two that spilled over.
_SHORT_LAST_PAGE = 80
_LISTED = 4


def page_problems(pdf_path: Path) -> dict[str, Any]:
    """`{"pages": n, "problems": [...]}` for the PDF of a document; empty problems when its pages
    look right. Raises what PDFium raises for a file it cannot open."""
    import pypdfium2 as pdfium

    with PDFIUM_LOCK:
        document = pdfium.PdfDocument(str(pdf_path))
        try:
            counts = [_page_facts(document[index]) for index in range(len(document))]
        finally:
            document.close()
    problems = []
    empty = [
        str(n) for n, (letters, objects, _) in enumerate(counts, 1) if not letters and not objects
    ]
    if empty:
        problems.append(f"empty page: {_listed(empty)}")
    past = [str(n) for n, (_, _, off) in enumerate(counts, 1) if off]
    if past:
        problems.append(
            f"text runs past the paper's edge (a table or line too wide): page {_listed(past)}"
        )
    if len(counts) > 1 and 0 < counts[-1][0] < _SHORT_LAST_PAGE:
        problems.append(
            f"page {len(counts)}, the last, holds only a line or two: fit it on the page before"
        )
    return {"pages": len(counts), "problems": problems}


def _page_facts(page: Any) -> tuple[int, int, bool]:
    """Letters on the page, its objects (text, pictures, drawings), and whether a letter lies past
    the paper's edge."""
    width, height = page.get_size()
    textpage = page.get_textpage()
    letters, off = 0, False
    for index in range(textpage.count_chars()):
        if textpage.get_text_range(index, 1).isspace():
            continue
        letters += 1
        left, bottom, right, top = textpage.get_charbox(index)
        if (
            left < -_EDGE_PT
            or right > width + _EDGE_PT
            or bottom < -_EDGE_PT
            or top > height + _EDGE_PT
        ):
            off = True
    return letters, sum(1 for _ in page.get_objects()), off


def _listed(pages: list[str]) -> str:
    shown = ", ".join(pages[:_LISTED])
    return shown + (f" and {len(pages) - _LISTED} more" if len(pages) > _LISTED else "")


def checked_pages(check: dict[str, Any]) -> dict[str, Any] | str:
    """What a write tool returns as `page_check`: the check an office program filled, or why there
    is none. It is never reported as a pass when it could not run."""
    return check or "not checked (needs Microsoft Office, WPS Office or LibreOffice)"
