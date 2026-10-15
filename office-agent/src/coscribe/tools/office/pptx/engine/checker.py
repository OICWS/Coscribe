"""Check a compiled deck for what the converter cannot refuse but a reader would see.

The compiler reports what it could not convert. These checks look at what it did convert, in the
coordinates PowerPoint will use: the emitter has already measured every text line with the
metrics of its font, so a text frame's box tells where its glyphs are. Errors are defects to
repair (text past the page edge, text drawn over text, text that cannot be read); warnings are
for the model to judge (faint text, a number no source file has, which may be a sum it computed).

The thresholds were set on 130 pages written by a model in the research behind decision 0010
(`docs/assessments/2026-10-13-office-route.md`), against their renders: each flags the pages a
person would fix and leaves the ones the judges rated best alone.
"""

from __future__ import annotations

import copy
import math
import re
import unicodedata
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from pptx import Presentation

from ...._native_svg.svg_to_pptx.drawingml.utils import estimate_text_width
from ...._ooxml_validate import ooxml_errors
from .compiler import EMU_PER_PX, CompileReport

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_DRAWN = (f"{_P}sp", f"{_P}pic", f"{_P}cxnSp")
_PX_PER_PT = 96 / 72
# A crossing smaller than this is anti-aliasing, not a defect anyone can see.
_TOLERANCE_PX = 2.0
# A text frame is larger than its glyphs. Vertically it runs from about 0.97 em above the
# baseline to 0.55 em below, while glyphs stay within 0.8 em above (CJK ideographs; capitals and
# digits 0.75 em) and 0.15 em below. Horizontally the emitter adds headroom to the measured
# advance, about a sixth of the width in the decks measured, on the side the line grows towards.
# Without these a large number and the unit beside it, or a label under it, collide as boxes but
# not as glyphs.
_INK_TOP_EM, _INK_BOTTOM_EM = 0.17, 0.40
_INK_WIDTH = 1 / 1.2
# Glyphs of two texts sharing less than this share of the smaller one's height only touch.
_OVERLAP_SHARE = 0.2
# WCAG's 3:1 (its minimum for large text) for all text: 4.5:1 flags the light grey captions of
# decks the judges rated best. Below 1.5:1 nobody can read it (white on white): an error.
_MIN_CONTRAST = 3.0
_UNREADABLE = 1.5
_WATERMARK_CHARS = 3
# A page with many faint texts gets one line naming the worst, not one line each.
_LISTED = 4
# A page number, a month or a day is not a claim about the world.
_SMALL_INTEGER = 31
# A count in one unit is written in another on a page: 261.5 万 as 2.615 million or 2,615,000,
# so a number is known when the sources have it as written or by value.
_MAGNITUDES = {
    "万亿": 10**12,
    "千万": 10**7,
    "百万": 10**6,
    "亿": 10**8,
    "万": 10**4,
    "千": 10**3,
    "trillion": 10**12,
    "billion": 10**9,
    "million": 10**6,
    "thousand": 10**3,
    "bn": 10**9,
    "mn": 10**6,
}
# A power of ten from a thousand up in brackets, as a page names the unit an axis or column counts.
_UNIT_LABEL = re.compile(r"[(（][^()（）\d]*\b10(?:,?000)+\b[^()（）\d]*[)）]")
# A one-letter abbreviation counts only right after the digits (2.615m, 267k), not as a word.
_LETTERS = {"k": 10**3, "m": 10**6, "b": 10**9}
_VALUE = re.compile(
    r"(\d+(?:\.\d+)?)(?:\s*(" + "|".join(sorted(_MAGNITUDES, key=len, reverse=True)) + ")"
    r"|([kmb])(?![a-z]))?",
    re.IGNORECASE,
)
# The schema forbids `xml:space` on a text run, which the emitter writes to keep a run's edge
# spaces; PowerPoint accepts it (the part 1 deck that opened without a repair prompt on Windows
# has it), so it is removed from the copy that is validated.
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_SCHEMA_PREFIX = re.compile(r"^.*?ERROR:SCHEMASV:\w+: ")
# PowerPoint's default cell margins (0.1 in left and right, 0.05 in top and bottom) and the line
# height it gives a cell's text.
_CELL_MARGIN_X, _CELL_MARGIN_Y, _CELL_LINE = 9.6, 4.8, 1.2


@dataclass(frozen=True)
class _Box:
    left: float
    top: float
    right: float
    bottom: float

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom


@dataclass(frozen=True)
class _Text:
    text: str
    ink: _Box
    # The lowest contrast of its runs against what is drawn behind it; None over a picture.
    contrast: float | None
    colour: str
    behind: str | None


def check_deck(report: CompileReport, sources: Sequence[str] | None = None) -> None:
    """Add each page's findings to its page report.

    `sources` are the texts the deck was made from; without them the number check is skipped,
    since every number would look invented."""
    prs = Presentation(str(report.path))
    # The compiler always sets the slide size, so neither is None here.
    width, height = int(prs.slide_width or 0) / EMU_PER_PX, int(prs.slide_height or 0) / EMU_PER_PX
    known = known_numbers("\n".join(sources)) if sources is not None else None
    for page, slide in zip(report.pages, prs.slides, strict=True):
        page.errors.extend(_schema(slide._element))
        texts = _texts(slide._element)
        page.errors.extend(_outside(texts, width, height))
        page.errors.extend(_overlaps(texts))
        page.errors.extend(_grown_tables(slide._element, texts, height))
        unreadable, faint = _contrast(texts)
        page.errors.extend(unreadable)
        page.warnings.extend(faint)
        if known is not None:
            page.warnings.extend(_unknown_numbers(texts + _data(slide), known))


def _schema(slide: Any) -> Iterator[str]:
    """What PowerPoint's schema rejects on the slide: a file with such XML can open with a
    repair prompt or not at all, so it is an error even when LibreOffice renders it."""
    checked = copy.deepcopy(slide)
    for run in checked.iter(f"{_A}t"):
        run.attrib.pop(_XML_SPACE, None)
    for error in ooxml_errors(checked)[:_LISTED]:
        yield f"the slide breaks PowerPoint's file format: {_SCHEMA_PREFIX.sub('', error)}"


def _texts(slide: Any) -> list[_Text]:
    """The slide's text frames, with what is painted behind each. Drawing order is document
    order, and the compiler writes each group with its child frame equal to its own, so every
    offset is already a position on the slide."""
    painted: list[tuple[_Box, Any]] = []
    texts: list[_Text] = []
    background = _background(slide)
    for element in slide.iter(*_DRAWN):
        box = _box(element)
        if box is None:
            continue
        text = "".join(t.text or "" for t in element.iter(f"{_A}t")).strip()
        if text:
            x, y = (box.left + box.right) / 2, (box.top + box.bottom) / 2
            behind: str | None = background
            for under, under_element in painted:
                if under.contains(x, y):
                    behind = _paint_over(behind, under_element)
            colours = [_effective(c, behind) for c in _run_colours(element)]
            contrast, colour = None, ""
            if behind is not None and colours:
                contrast, colour = min((_contrast_ratio(c, behind), c) for c in colours)
            texts.append(_Text(text, _ink(element, box), contrast, colour, behind))
        painted.append((box, element))
    return texts


def _box(element: Any) -> _Box | None:
    xfrm = element.find(f".//{_A}xfrm")
    off = xfrm.find(f"{_A}off") if xfrm is not None else None
    ext = xfrm.find(f"{_A}ext") if xfrm is not None else None
    if off is None or ext is None:
        return None
    left, top = int(off.get("x")) / EMU_PER_PX, int(off.get("y")) / EMU_PER_PX
    return _Box(
        left, top, left + int(ext.get("cx")) / EMU_PER_PX, top + int(ext.get("cy")) / EMU_PER_PX
    )


def _ink(element: Any, box: _Box) -> _Box:
    sizes = [int(r.get("sz")) for r in element.iter(f"{_A}rPr") if r.get("sz")]
    em = max(sizes) / 100 * _PX_PER_PT if sizes else 0.0
    top, bottom = box.top + _INK_TOP_EM * em, box.bottom - _INK_BOTTOM_EM * em
    width = (box.right - box.left) * _INK_WIDTH
    p_pr = element.find(f".//{_A}pPr")
    align = p_pr.get("algn", "l") if p_pr is not None else "l"
    if align == "r":
        return _Box(box.right - width, top, box.right, bottom)
    if align == "ctr":
        middle = (box.left + box.right) / 2
        return _Box(middle - width / 2, top, middle + width / 2, bottom)
    return _Box(box.left, top, box.left + width, bottom)


def _quote(text: str) -> str:
    return f'"{text[:40]}…"' if len(text) > 40 else f'"{text}"'


def _outside(texts: list[_Text], width: float, height: float) -> Iterator[str]:
    for t in texts:
        sides = [
            name
            for name, past in (
                ("left", -t.ink.left),
                ("top", -t.ink.top),
                ("right", t.ink.right - width),
                ("bottom", t.ink.bottom - height),
            )
            if past > _TOLERANCE_PX
        ]
        if sides:
            yield (
                f"text {_quote(t.text)} runs past the {' and '.join(sides)} edge of the page "
                f"(x {t.ink.left:.0f} to {t.ink.right:.0f}, y {t.ink.top:.0f} to "
                f"{t.ink.bottom:.0f} on a {width:.0f} x {height:.0f} page): shorten it, break it "
                "into more lines or make it smaller"
            )


def _overlaps(texts: list[_Text]) -> Iterator[str]:
    # Faint text over other text is decoration (a large page number set behind a card) or is
    # already reported as hard to read.
    legible = [t for t in texts if t.contrast is None or t.contrast >= _MIN_CONTRAST]
    for i, a in enumerate(legible):
        for b in legible[i + 1 :]:
            wide = min(a.ink.right, b.ink.right) - max(a.ink.left, b.ink.left)
            high = min(a.ink.bottom, b.ink.bottom) - max(a.ink.top, b.ink.top)
            smaller = min(a.ink.bottom - a.ink.top, b.ink.bottom - b.ink.top)
            if wide > _TOLERANCE_PX and high > _OVERLAP_SHARE * smaller:
                yield (
                    f"text {_quote(a.text)} and text {_quote(b.text)} are drawn over each "
                    f"other (around x {max(a.ink.left, b.ink.left):.0f}, "
                    f"y {max(a.ink.top, b.ink.top):.0f}): move one or shorten it"
                )


def _grown_tables(slide: Any, texts: list[_Text], height: float) -> Iterator[str]:
    """A table's rows grow when a cell's text wraps, so its bottom is lower than its frame says;
    reported only where the grown table runs into text or off the page."""
    for frame in slide.iter(f"{_P}graphicFrame"):
        table = frame.find(f".//{_A}tbl")
        xfrm = frame.find(f"{_P}xfrm")
        if table is None or xfrm is None:
            continue
        off, ext = xfrm.find(f"{_A}off"), xfrm.find(f"{_A}ext")
        left, top = int(off.get("x")) / EMU_PER_PX, int(off.get("y")) / EMU_PER_PX
        right = left + int(ext.get("cx")) / EMU_PER_PX
        stated = top + int(ext.get("cy")) / EMU_PER_PX
        bottom = top + _table_height(table)
        if bottom <= stated + _TOLERANCE_PX:
            continue
        hit = [
            t
            for t in texts
            if min(t.ink.right, right) - max(t.ink.left, left) > _TOLERANCE_PX
            and min(t.ink.bottom, bottom) - max(t.ink.top, stated) > _TOLERANCE_PX
        ]
        if not hit and bottom <= height:
            continue
        name = frame.find(f".//{_P}cNvPr").get("name", "")
        over = f"over text {_quote(hit[0].text)}" if hit else "past the bottom of the page"
        yield (
            f"table {name!r}: cells whose text wraps make its rows taller, so it reaches y "
            f"{bottom:.0f} instead of {stated:.0f}, {over}: widen the narrow columns, shorten "
            "the long cells, use smaller text or fewer rows"
        )


def _table_height(table: Any) -> float:
    widths = [int(c.get("w")) / EMU_PER_PX for c in table.iter(f"{_A}gridCol")]
    total = 0.0
    for row in table.iter(f"{_A}tr"):
        height = int(row.get("h", 0)) / EMU_PER_PX
        for width, cell in zip(widths, row.findall(f"{_A}tc"), strict=False):
            if cell.get("hMerge") or cell.get("vMerge") or cell.get("gridSpan"):
                continue
            sizes = [int(r.get("sz")) for r in cell.iter(f"{_A}rPr") if r.get("sz")]
            size = (max(sizes) / 100 if sizes else 18) * _PX_PER_PT
            inner = max(width - 2 * _CELL_MARGIN_X, 1.0)
            lines = sum(
                max(1, math.ceil(estimate_text_width(_cell_text(p), size) / inner))
                for p in cell.iter(f"{_A}p")
            )
            height = max(height, lines * size * _CELL_LINE + 2 * _CELL_MARGIN_Y)
        total += height
    return total


def _cell_text(paragraph: Any) -> str:
    return "".join(t.text or "" for t in paragraph.iter(f"{_A}t"))


def _contrast(texts: list[_Text]) -> tuple[list[str], list[str]]:
    unreadable: list[str] = []
    faint: list[tuple[float, str]] = []
    for t in texts:
        if t.contrast is None or t.contrast >= _MIN_CONTRAST:
            continue
        described = f"{_quote(t.text)} #{t.colour} on #{t.behind} ({t.contrast:.1f}:1)"
        if t.contrast < _UNREADABLE:
            # A watermark digit or two is drawn this faint on purpose.
            if len(t.text) > _WATERMARK_CHARS:
                unreadable.append(
                    f"text {described} cannot be read: change its colour or what is behind it"
                )
        else:
            faint.append((t.contrast, described))
    warnings = []
    if faint:
        faint.sort()
        more = f" and {len(faint) - _LISTED} more" if len(faint) > _LISTED else ""
        warnings.append(
            f"text hard to read, contrast below {_MIN_CONTRAST:g}:1: "
            + "; ".join(text for _ratio, text in faint[:_LISTED])
            + f"{more}. Darken the text or lighten what is behind it, unless it is decoration "
            "meant to be faint"
        )
    return unreadable, warnings


def _background(slide: Any) -> str:
    colour = slide.find(f"{_P}cSld/{_P}bg//{_A}srgbClr")
    return str(colour.get("val")).upper() if colour is not None else "FFFFFF"


def _paint_over(below: str | None, element: Any) -> str | None:
    """The colour seen through `element` drawn over `below`. A picture hides what is under it
    (None: unknown), a translucent fill is blended, a gradient counts as the mean of its stops,
    and a shape without a fill (an outline, a text frame) leaves `below` as it was."""
    if element.tag == f"{_P}pic":
        return None
    sp_pr = element.find(f"{_P}spPr")
    if sp_pr is None:
        return below
    solid = sp_pr.find(f"{_A}solidFill/{_A}srgbClr")
    paints = (
        [solid]
        if solid is not None
        else sp_pr.findall(f"{_A}gradFill/{_A}gsLst/{_A}gs/{_A}srgbClr")
    )
    if not paints:
        return below
    rgb = [_rgb(str(c.get("val"))) for c in paints]
    mean = "".join(f"{round(sum(c[i] for c in rgb) / len(rgb)):02X}" for i in range(3))
    alpha = sum(_alpha(c) for c in paints) / len(paints)
    if alpha >= 1:
        return mean
    return None if below is None else _blend(mean, alpha, below)


def _run_colours(element: Any) -> Iterator[Any]:
    yield from element.iterfind(f".//{_A}rPr/{_A}solidFill/{_A}srgbClr")


def _effective(colour: Any, behind: str | None) -> str:
    """A translucent text colour as it shows over what is behind it."""
    value, alpha = str(colour.get("val")).upper(), _alpha(colour)
    return value if alpha >= 1 or behind is None else _blend(value, alpha, behind)


def _alpha(colour: Any) -> float:
    """The emitter writes a fill's opacity as `alpha` and a text run's as `alphaMod`."""
    alpha = 1.0
    for tag in ("alpha", "alphaMod"):
        found = colour.find(f"{_A}{tag}")
        if found is not None:
            alpha *= int(found.get("val")) / 100000
    return alpha


def _blend(top: str, alpha: float, below: str) -> str:
    return "".join(
        f"{round(t * alpha + b * (1 - alpha)):02X}"
        for t, b in zip(_rgb(top), _rgb(below), strict=True)
    )


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    return int(hex_colour[0:2], 16), int(hex_colour[2:4], 16), int(hex_colour[4:6], 16)


def _luminance(hex_colour: str) -> float:
    def linear(channel: int) -> float:
        c = channel / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linear(c) for c in _rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(a: str, b: str) -> float:
    light, dark = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _data(slide: Any) -> list[_Text]:
    """What a native chart or table on the slide shows: its cells, categories and values.
    A chart's data lives in its own part, outside the slide's XML."""
    found: list[str] = []
    for frame in slide._element.iter(f"{_P}graphicFrame"):
        found.extend(t.text or "" for t in frame.iter(f"{_A}t"))
    for shape in slide.shapes:
        for chart in _charts(shape):
            for plot in chart.plots:
                found.extend(str(category) for category in plot.categories)
                for series in plot.series:
                    found.extend(_plain(value) for value in series.values if value is not None)
    return [_Text(text, _Box(0, 0, 0, 0), None, "", None) for text in found if text.strip()]


def _charts(shape: Any) -> Iterator[Any]:
    if getattr(shape, "has_chart", False) and shape.has_chart:
        yield shape.chart
    for member in getattr(shape, "shapes", ()):
        yield from _charts(member)


def _plain(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else repr(value)


def number_values(text: str) -> list[tuple[str, Decimal]]:
    """Every number in `text` as written, with its value in ones: 261.5 万 is 2615000."""
    folded = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", unicodedata.normalize("NFKC", text))
    found = []
    for number, word, letter in _VALUE.findall(folded):
        scale = _MAGNITUDES.get(word.lower()) or _LETTERS.get(letter.lower(), 1)
        found.append((number, Decimal(number) * scale))
    return found


def known_numbers(text: str) -> set[str | Decimal]:
    """The numbers of a source, both as written and by value, for `is_known`."""
    return {item for pair in number_values(text) for item in pair}


def is_claim(number: str) -> bool:
    """Whether a number says something about the world; a page number or a day does not."""
    return "." in number or int(number) > _SMALL_INTEGER


def claims(text: str) -> list[tuple[str, Decimal]]:
    """The numbers of `text` that are claims, each with its value, leaving out a unit spelled
    out in brackets: "(10,000 units)" under a 万辆 axis says what the axis counts."""
    return [(n, v) for n, v in number_values(_UNIT_LABEL.sub(" ", text)) if is_claim(n)]


def is_known(number: str, value: Decimal, known: set[str | Decimal]) -> bool:
    return number in known or value in known


def _unknown_numbers(texts: list[_Text], known: set[str | Decimal]) -> Iterator[str]:
    values = claims("\n".join(t.text for t in texts))
    found = sorted(
        {n for n, v in values if not is_known(n, v, known)},
        key=float,
    )
    if found:
        yield (
            f"numbers no source file has: {', '.join(found)}. Axis ticks and figures computed "
            "from the sources are fine; a number that is neither must come out"
        )


def source_text(path: Path) -> str:
    """The text of a file the deck is made from, for the number check."""
    suffix = path.suffix.lower()
    if suffix == ".docx":
        from docx import Document

        document = Document(str(path))
        cells = (c.text for t in document.tables for row in t.rows for c in row.cells)
        return "\n".join([*(p.text for p in document.paragraphs), *cells])
    if suffix == ".xlsx":
        from openpyxl import load_workbook

        book = load_workbook(str(path), data_only=True, read_only=True)
        values = (v for sheet in book for row in sheet.iter_rows(values_only=True) for v in row)
        return "\n".join(str(v) for v in values if v is not None)
    if suffix == ".pptx":
        deck = Presentation(str(path))
        return "\n".join(t.text or "" for s in deck.slides for t in s._element.iter(f"{_A}t"))
    if suffix == ".pdf":
        from ...pdf.text import _pdf_page_texts

        return "\n".join(text for _page, text in _pdf_page_texts(path))
    return path.read_text(encoding="utf-8", errors="replace")
