"""Column widths for pipe tables, measured in ems; shared by the docx and pdf writers."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .markdown_blocks import parse_inline_runs

_CJK_CHARS = "\u2e80-\u9fff\uac00-\ud7af\uf900-\ufaff\uff00-\uffef"
_CJK_RE = re.compile(f"[{_CJK_CHARS}]")

_NUMBER_CELL_RE = re.compile(r"^[+\-\u2212]?[¥$€£]?\d[\d,]*(?:\.\d+)?\s*[%‰]?$")
# Breaking a line is allowed between CJK characters and at spaces, so these
# runs are the pieces a cell can never be narrower than.
_UNBREAKABLE_RE = re.compile(f"[{_CJK_CHARS}]|[^\\s{_CJK_CHARS}]+")
_SHORT_CELL_EM = 6.0


def _text_width_em(text: str) -> float:
    """Rendered width in ems, measured on DejaVu Sans -- what LibreOffice
    falls back to without Calibri, and wider than Calibri, Arial or YaHei --
    so a cell measured here fits in any of them."""
    width = 0.0
    for ch in text:
        if _CJK_RE.match(ch):
            width += 1.0
        elif ch.isdigit():
            width += 0.64
        elif ch in ",.:;'|!ilj ":
            width += 0.32
        elif ch in "%@mwMW":
            width += 0.95
        elif ch.isupper():
            width += 0.72
        else:
            width += 0.58
    return width


def _cell_width_em(cell: str, pieces: bool = False, bold: bool = False) -> float:
    """The cell's full width in ems, or with `pieces` its widest unbreakable
    piece; bold text runs about a tenth wider. `bold` is for a cell the writer
    makes bold without markup, a header row."""
    runs = parse_inline_runs(cell)
    text = "".join(run_text for run_text, _, _ in runs)
    scale = 1.1 if bold or any(run_bold for _, run_bold, _ in runs) else 1.0
    if pieces:
        return scale * max((_text_width_em(p) for p in _UNBREAKABLE_RE.findall(text)), default=0)
    return scale * _text_width_em(text)


def _plain_cell_text(cell: str) -> str:
    return "".join(run_text for run_text, _, _ in parse_inline_runs(cell))


def _is_number_cell(cell: str) -> bool:
    return bool(_NUMBER_CELL_RE.match(_plain_cell_text(cell).strip()))


def _numeric_columns(rows: list[list[str]], header: bool) -> list[bool]:
    """A column whose every filled body cell is a number (amounts, counts,
    percentages) -- right-aligned, so the digits line up."""
    columns = max(len(row) for row in rows)
    body = rows[1:] if header else rows
    result = []
    for index in range(columns):
        cells = [row[index] for row in body if index < len(row) and row[index].strip()]
        result.append(bool(cells) and all(_is_number_cell(cell) for cell in cells))
    return result


def _share_out(total: float, low: list[float], high: list[float]) -> list[float]:
    """`low` plus whatever of `total` is left, given in proportion to how
    far each column is below `high`."""
    spare = total - sum(low)
    wants = [h - lo for h, lo in zip(high, low, strict=True)]
    if sum(wants) <= 0:
        return [total * width / sum(low) for width in low]
    return [lo + spare * want / sum(wants) for lo, want in zip(low, wants, strict=True)]


def _table_layout(
    rows: list[list[str]],
    total: float,
    font_sizes: Sequence[float],
    padding: float,
    header: bool = False,
) -> tuple[float, list[float]]:
    """(font size, column widths in points adding up to `total`).

    In order of what gives way last: no column narrower than its longest
    unbreakable piece (an amount like 23,457,888.42, a word), so no number
    wraps mid-way; then short cells (a label like 控制器, a header) kept on
    one line; the rest goes to the columns whose long text wraps anyway.
    Uses the first of `font_sizes` (largest first) at which the short cells
    fit, else the first at which the pieces fit, else the last. With `header`
    the first row is measured bold, as the writers set it."""
    columns = max(len(row) for row in rows)
    piece_em, full_em = [], []
    for index in range(columns):
        cells = [
            (row_number == 0 and header, row[index])
            for row_number, row in enumerate(rows)
            if index < len(row)
        ]
        piece_em.append(
            max((_cell_width_em(c, pieces=True, bold=b) for b, c in cells), default=0.0)
        )
        full_em.append(max((_cell_width_em(c, bold=b) for b, c in cells), default=0.0))

    def widths_at(font_size: float) -> tuple[list[float], list[float], list[float]]:
        floor = 2 * font_size + padding
        hard = [max(em * font_size + padding, floor) for em in piece_em]
        natural = [max(em * font_size + padding, floor) for em in full_em]
        short = [
            max(h, min(n, _SHORT_CELL_EM * font_size + padding))
            for h, n in zip(hard, natural, strict=True)
        ]
        return hard, short, natural

    font_size = next(
        (size for size in font_sizes if sum(widths_at(size)[1]) <= total),
        next((size for size in font_sizes if sum(widths_at(size)[0]) <= total), font_sizes[-1]),
    )
    hard, short, natural = widths_at(font_size)
    if sum(natural) <= total:
        return font_size, [total * width / sum(natural) for width in natural]
    if sum(short) <= total:
        return font_size, _share_out(total, short, natural)
    if sum(hard) <= total:
        return font_size, _share_out(total, hard, short)
    return font_size, [total * width / sum(hard) for width in hard]
