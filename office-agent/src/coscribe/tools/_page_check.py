"""What a generated document's pages look like once an office program has laid them out (decision
0026): an empty page, text that runs past the paper's edge (a table too wide), and a last page that
holds only a line or two. The file alone can't say any of this; only the PDF the program made can.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._pdfium import PDFIUM_LOCK

# A character this far past the paper (in points) has left it; nearer is rounding.
_EDGE_PT = 1.0
# A last page with fewer letters than this is a line or two that spilled over.
_SHORT_LAST_PAGE = 80
# A page whose body reaches this near its foot (a share of its height) is full, so a short page
# after it is a spill; a short page after a half-empty one was put there on purpose (a signature
# after a page break).
_FULL_PAGE_FOOT = 0.2
# Headers, footers and page numbers sit in this share of the page at its top or foot.
_MARGIN_BAND = 0.12
_LISTED = 4
# Not letters: PDFium's markers for a soft hyphen and a generated line end.
_NOT_LETTERS = "\x02￾"


@dataclass
class _Page:
    # (baseline, text with digits as '#') -> letters: a header, footer or "Page 3 of 5" has the
    # same key on every page it repeats on.
    lines: Counter[tuple[int, str]] = field(default_factory=Counter)
    lowest: dict[tuple[int, str], float] = field(default_factory=dict)
    in_margin: set[tuple[int, str]] = field(default_factory=set)
    drawings: list[tuple[int, tuple[int, ...]]] = field(default_factory=list)
    off: bool = False
    height: float = 0.0


def page_problems(pdf_path: Path) -> dict[str, Any]:
    """`{"pages": n, "problems": [...]}` for the PDF of a document; empty problems when its pages
    look right. Raises what PDFium raises for a file it cannot open."""
    import pypdfium2 as pdfium

    with PDFIUM_LOCK:
        document = pdfium.PdfDocument(str(pdf_path))
        try:
            pages = [_page_facts(document[index]) for index in range(len(document))]
        finally:
            document.close()
    repeated = _repeated(pages)
    body = [{key: n for key, n in page.lines.items() if key not in repeated} for page in pages]
    letters = [sum(lines.values()) for lines in body]
    problems = []
    empty = [
        str(n)
        for n, (page, count) in enumerate(zip(pages, letters, strict=True), 1)
        if not count and all(key in repeated for key in page.drawings)
    ]
    if empty:
        problems.append(f"empty page: {_listed(empty)}")
    past = [str(n) for n, page in enumerate(pages, 1) if page.off]
    if past:
        problems.append(
            f"text runs past the paper's edge (a table or line too wide): page {_listed(past)}"
        )
    if len(pages) > 1 and 0 < letters[-1] < _SHORT_LAST_PAGE and _full(pages[-2], body[-2]):
        problems.append(
            f"page {len(pages)}, the last, holds only a line or two: fit it on the page before"
        )
    return {"pages": len(pages), "problems": problems}


def _page_facts(page: Any) -> _Page:
    """The page's lines of letters, its other objects (pictures, drawings) by place, and whether
    a letter lies past the paper. The character boxes are in the unrotated page space, so the edge
    is the MediaBox, not the rotated size."""
    import pypdfium2.raw as pdfium_c

    left_edge, bottom_edge, right_edge, top_edge = page.get_mediabox()
    facts = _Page(height=max(top_edge - bottom_edge, 1.0))  # a malformed box has none
    textpage = page.get_textpage()
    words: dict[int, list[str]] = {}
    lowest: dict[int, float] = {}
    for position, char in enumerate(textpage.get_text_range()):
        if char.isspace() or char in _NOT_LETTERS:
            continue
        left, bottom, right, top = textpage.get_charbox(position)
        baseline = round(bottom)
        words.setdefault(baseline, []).append(char)
        lowest[baseline] = bottom - bottom_edge
        if (
            left < left_edge - _EDGE_PT
            or right > right_edge + _EDGE_PT
            or bottom < bottom_edge - _EDGE_PT
            or top > top_edge + _EDGE_PT
        ):
            facts.off = True
    for baseline, chars in words.items():
        key = (baseline, "".join("#" if c.isdigit() else c for c in chars))
        facts.lines[key] += len(chars)
        facts.lowest[key] = lowest[baseline]
        if not _MARGIN_BAND < lowest[baseline] / facts.height < 1 - _MARGIN_BAND:
            facts.in_margin.add(key)
    facts.drawings = [
        (obj.type, tuple(round(v) for v in obj.get_bounds()))
        for obj in page.get_objects()
        if obj.type != pdfium_c.FPDF_PAGEOBJ_TEXT
    ]
    return facts


def _repeated(pages: list[_Page]) -> set[Any]:
    """Lines in the top or foot band, and drawings anywhere, at the same place on most pages: the
    header, footer, page number and logo every page carries, which keep neither an empty page from
    being empty nor count as body. A body line that happens to repeat is not in the band."""
    if len(pages) < 2:
        return set()
    seen: Counter[Any] = Counter()
    for page in pages:
        seen.update(page.in_margin | set(page.drawings))
    return {key for key, n in seen.items() if n >= 2 and n * 2 > len(pages)}


def _full(page: _Page, body: dict[tuple[int, str], int]) -> bool:
    return bool(body) and min(page.lowest[key] for key in body) < page.height * _FULL_PAGE_FOOT


def _listed(pages: list[str]) -> str:
    shown = ", ".join(pages[:_LISTED])
    return shown + (f" and {len(pages) - _LISTED} more" if len(pages) > _LISTED else "")


def checked_pages(
    check: dict[str, Any], preview_skipped_reason: str | None
) -> dict[str, Any] | str:
    """What a write tool returns as `page_check`: the check an office program filled, or why there
    is none, from what really happened. It is never reported as a pass when it could not run."""
    if "problems" in check:
        return check
    return f"not checked ({check.get('failed') or preview_skipped_reason or 'no office program'})"
