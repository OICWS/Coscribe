"""Column widths for the xlsx tools: a column is widened to what it shows, never narrowed."""

from __future__ import annotations

import re
import zipfile
from copy import copy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree as ET

from .column_widths import DEFAULT_WIDTH, MAX_WIDTH, needed_width

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

_PARTS_NAMING_SHEETS = ("xl/workbook.xml", "xl/_rels/workbook.xml.rels")


@dataclass
class Span:
    """One `<col>` element: a run of columns with the same width and look."""

    min: int
    max: int
    width: float | None = None
    look: dict[str, Any] = field(default_factory=dict)
    style: Any = None


def explicit_width_starts(path: Path, sheet_name: str) -> set[int]:
    """The first column of each `<col>` that carries a width; openpyxl gives one without a width
    (only hidden, styled or outlined) a width of 13, so the file itself is read."""
    from ..._xlsx_lookup_formulas import _sheet_archive_paths

    with zipfile.ZipFile(path) as archive:
        part = _sheet_archive_paths({name: archive.read(name) for name in _PARTS_NAMING_SHEETS})
        if sheet_name not in part:
            return set()
        starts = set()
        with archive.open(part[sheet_name]) as stream:
            for _, element in ET.iterparse(stream, events=("start",)):
                if element.tag.endswith("}col") and element.get("width") is not None:
                    starts.add(int(element.get("min", "0")))
                elif element.tag.endswith("}sheetData"):
                    break
    return starts


def sheet_spans(sheet: Worksheet, width_starts: set[int]) -> list[Span]:
    """The sheet's columns as they are, with a width only where the file sets one."""
    from openpyxl.utils import column_index_from_string

    spans = []
    dimensions: dict[str, Any] = dict(sheet.column_dimensions)
    for letter, dimension in dimensions.items():
        first = dimension.min or column_index_from_string(letter)
        look = {
            "hidden": bool(dimension.hidden),
            "outlineLevel": dimension.outlineLevel or 0,
            "collapsed": bool(dimension.collapsed),
        }
        spans.append(
            Span(
                first,
                dimension.max or first,
                float(dimension.width or 0) if first in width_starts else None,
                look,
                copy(dimension._style) if dimension.has_style else None,
            )
        )
    return spans


def _span_at(spans: list[Span], column: int) -> Span | None:
    return next((span for span in spans if span.min <= column <= span.max), None)


def _shown_width(span: Span | None) -> float:
    if span is None:
        return DEFAULT_WIDTH
    if span.look.get("hidden"):
        return 0.0
    return DEFAULT_WIDTH if span.width is None else span.width


def _own_span(spans: list[Span], column: int) -> Span:
    """The span of `column` alone, split out of the range it was part of."""
    for i, span in enumerate(spans):
        if span.min <= column <= span.max:
            own = replace(span, min=column, max=column, look=dict(span.look))
            pieces = [replace(span, max=column - 1)] if span.min < column else []
            pieces.append(own)
            if column < span.max:
                pieces.append(replace(span, min=column + 1))
            spans[i : i + 1] = pieces
            return own
    spans.append(own := Span(column, column))
    return own


def widen(spans: list[Span], needed: dict[int, float]) -> bool:
    """Give each column the width it needs, capped, unless it already has more; a hidden or
    zero-width column is left as someone made it."""
    changed = False
    for column, width in sorted(needed.items()):
        span = _span_at(spans, column)
        if span is not None and (span.look.get("hidden") or span.width == 0):
            continue
        target = round(min(width, MAX_WIDTH), 2)
        if target > _shown_width(span):
            _own_span(spans, column).width = target
            changed = True
    return changed


def _empty(value: Any) -> bool:
    return value is None or value == ""


def _needed(sheet: Worksheet, spans: list[Span]) -> dict[int, float]:
    needed: dict[int, float] = {}
    last = sheet.max_column
    spilling = []
    for row in sheet.iter_rows():
        filled = [cell for cell in row if not _empty(cell.value)]
        for column, cell in enumerate(row, start=1):
            # A label alone in its row (a title over a table) runs on past the table's last
            # column, so it never needs a width of its own.
            if filled == [cell] and isinstance(cell.value, str):
                continue
            # A formula has no value before LibreOffice recalculates the saved file; its header
            # and the constants beside it size the column.
            if cell.data_type == "f":
                continue
            width = needed_width(cell.value, cell.number_format)
            if isinstance(cell.value, str) and column < last and _empty(row[column].value):
                spilling.append((row, column, width))
                continue
            needed[column] = max(needed.get(column, 0.0), width)

    def shown(column: int) -> float:
        return max(_shown_width(_span_at(spans, column)), min(needed.get(column, 0.0), MAX_WIDTH))

    # Text runs on over the empty cells to its right, up to the sheet's last column (where a
    # printed page cuts it); only text longer than that run widens its own column.
    for row, column, width in spilling:
        room, right = shown(column), column + 1
        while right <= last and _empty(row[right - 1].value):
            room += shown(right)
            right += 1
        if width > room:
            needed[column] = max(needed.get(column, 0.0), width)
    return needed


def _exact_width_dimension() -> type:
    from openpyxl.worksheet.dimensions import ColumnDimension

    class ExactWidth(ColumnDimension):
        # openpyxl leaves out every falsy attribute, so a width of 0 (a column someone closed)
        # would come back at the default width.
        def __iter__(self) -> Any:
            yield from super().__iter__()
            yield "width", "0"
            yield "customWidth", "1"

    return ExactWidth


def apply_spans(sheet: Worksheet, spans: list[Span]) -> None:
    """Replace the sheet's column dimensions with `spans`."""
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.dimensions import ColumnDimension

    sheet.column_dimensions.clear()
    for span in sorted(spans, key=lambda s: s.min):
        if span.width is None and not (any(span.look.values()) or span.style):
            continue
        letter = get_column_letter(span.min)
        kind = _exact_width_dimension() if span.width == 0 else ColumnDimension
        dimension: Any = kind(
            sheet, index=letter, width=span.width or 0, min=span.min, max=span.max, **span.look
        )
        if span.style is not None:
            dimension._style = copy(span.style)
        sheet.column_dimensions[letter] = dimension


def fit_columns(sheet: Worksheet, spans: list[Span]) -> list[str]:
    """Lay `spans` onto `sheet`, each column widened to its longest shown value; a hidden column
    that now holds data is shown again. Returns the formula cells, which have no value to measure
    until LibreOffice recalculates."""
    filled = {
        column
        for row in sheet.iter_rows()
        for column, cell in enumerate(row, start=1)
        if not _empty(cell.value)
    }
    for column in sorted(filled):
        span = _span_at(spans, column)
        if span is not None and span.look.get("hidden"):
            _own_span(spans, column).look["hidden"] = False
    widen(spans, _needed(sheet, spans))
    apply_spans(sheet, spans)
    return [cell.coordinate for row in sheet.iter_rows() for cell in row if cell.data_type == "f"]


def _shown_in_own_column(
    sheet: Worksheet, cell: Any, merged: list[tuple[int, int, int, int]]
) -> bool:
    """False for a merged cell and for text with an empty cell to its right, which both have
    more room than their column."""
    if any(c1 <= cell.column <= c2 and r1 <= cell.row <= r2 for c1, r1, c2, r2 in merged):
        return False
    if not isinstance(cell.value, str) or cell.column >= sheet.max_column:
        return True
    # Read, not `sheet.cell()`, which would create the neighbour.
    right = sheet._cells.get((cell.row, cell.column + 1))
    return right is not None and not _empty(right.value)


def widen_for_values(
    sheet: Worksheet, values: Any, cells: list[Any], width_starts: set[int]
) -> None:
    """Widen the columns of `cells` to show each value under the cell's number format. `values`
    is the same sheet loaded with the computed values, for formula cells; without it a formula
    is not measured."""
    needed: dict[int, float] = {}
    merged = [tuple(merged.bounds) for merged in sheet.merged_cells.ranges]
    for cell in cells:
        if cell.data_type == "f" and values is None:
            continue
        value = values[cell.coordinate].value if cell.data_type == "f" else cell.value
        if _shown_in_own_column(sheet, cell, merged):
            needed[cell.column] = max(
                needed.get(cell.column, 0.0), needed_width(value, cell.number_format)
            )
    spans = sheet_spans(sheet, width_starts)
    if widen(spans, needed):
        apply_spans(sheet, spans)


def _col_xml(span: Span) -> str:
    sized = {} if span.width is None else {"width": f"{span.width:g}", "customWidth": "1"}
    look = {k: ("1" if v is True else "0" if v is False else str(v)) for k, v in span.look.items()}
    attributes = {**look, "min": str(span.min), "max": str(span.max), **sized}
    return ET.tostring(ET.Element("col", attributes), encoding="unicode")


def _xml_spans(cols: str) -> list[Span]:
    spans = []
    for col in ET.fromstring(cols) if cols else []:
        look: dict[str, Any] = {
            k: v for k, v in col.attrib.items() if k not in ("min", "max", "width", "customWidth")
        }
        look["hidden"] = look.get("hidden") in ("1", "true")
        size = col.get("width")
        first, last = int(col.get("min", "0")), int(col.get("max", "0"))
        spans.append(Span(first, last, float(size) if size else None, look))
    return spans


def _patch_cols(path: Path, sheet_name: str, needed: dict[int, float]) -> None:
    """Widen columns of `sheet_name` in the saved file by rewriting its `<cols>` only: an openpyxl
    save would drop every value LibreOffice computed."""
    from ..._xlsx_lookup_formulas import _sheet_archive_paths

    with zipfile.ZipFile(path) as archive:
        entries = {info.filename: archive.read(info.filename) for info in archive.infolist()}
        infos = archive.infolist()
    part = _sheet_archive_paths(entries).get(sheet_name)
    if part is None:
        return
    xml = entries[part].decode("utf-8")
    found = re.search(r"<cols>.*?</cols>|<cols/>", xml, re.DOTALL)
    start = found.start() if found else xml.find("<sheetData")
    end = found.end() if found else start
    spans = _xml_spans(found.group(0) if found else "")
    if start < 0 or not widen(spans, needed):
        return
    columns = "".join(_col_xml(span) for span in sorted(spans, key=lambda span: span.min))
    entries[part] = f"{xml[:start]}<cols>{columns}</cols>{xml[end:]}".encode()
    patched = path.with_name(path.name + ".cols")
    with zipfile.ZipFile(patched, "w", zipfile.ZIP_DEFLATED) as archive:
        for info in infos:
            archive.writestr(info, entries[info.filename])
    patched.replace(path)


def widen_after_recalc(path: Path, sheet_name: str, formula_cells: list[str]) -> None:
    """Widen the columns of `formula_cells` to the values LibreOffice computed for them."""
    from openpyxl import load_workbook

    if not formula_cells:
        return
    values = load_workbook(str(path), data_only=True)
    try:
        sheet = values[sheet_name]
        needed: dict[int, float] = {}
        for coordinate in formula_cells:
            cell = sheet[coordinate]
            needed[cell.column] = max(
                needed.get(cell.column, 0.0), needed_width(cell.value, cell.number_format)
            )
    finally:
        values.close()
    _patch_cols(path, sheet_name, needed)
