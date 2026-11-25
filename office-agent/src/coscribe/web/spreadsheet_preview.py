"""A sparse, read-only view of one worksheet and the workbook's sheet list."""

from __future__ import annotations

import math
from datetime import date, time, timedelta
from pathlib import Path
from typing import Any, BinaryIO
from zipfile import ZipFile

from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string, coordinate_to_tuple, range_boundaries
from openpyxl.xml.functions import iterparse

from ..tools.office.xlsx import displayed_text
from .spreadsheet_drawings import chart_references, drawings

_MAX_ARCHIVE = 32 * 1024 * 1024
_MAX_UNPACKED = 96 * 1024 * 1024
_MAX_CELLS = 80_000
_MAX_ROWS = 200_000
_MAX_COLUMNS = 16_384


class WorkbookTooLarge(ValueError):
    """The workbook is larger than this preview can safely open."""


def _check_size(stream: BinaryIO) -> None:
    stream.seek(0, 2)
    if stream.tell() > _MAX_ARCHIVE:
        raise WorkbookTooLarge
    with ZipFile(stream) as archive:
        if sum(item.file_size for item in archive.infolist()) > _MAX_UNPACKED:
            raise WorkbookTooLarge
        _check_expansion(archive)
    stream.seek(0)


def _check_expansion(archive: ZipFile) -> None:
    # openpyxl materializes every cell covered by a merged range, even when the XML is sparse.
    cells = 0
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    for entry in archive.infolist():
        if not entry.filename.endswith(".xml"):
            continue
        with archive.open(entry) as part:
            for _, element in iterparse(part):
                if element.tag == ns + "c":
                    cells += 1
                if element.tag == ns + "mergeCell":
                    left, top, right, bottom = range_boundaries(element.attrib["ref"])
                    if left is None or top is None or right is None or bottom is None:
                        raise ValueError("Incomplete merged range")
                    cells += (right - left + 1) * (bottom - top + 1)
                if cells > 240_000:
                    raise WorkbookTooLarge
                element.clear()


def _colour(color: Any) -> str | None:
    if color is None or color.type != "rgb":
        return None
    rgb = color.rgb[-6:]
    return f"#{rgb}" if len(rgb) == 6 and all(c in "0123456789abcdefABCDEF" for c in rgb) else None


def _style(cell: Any) -> dict[str, Any]:
    return {
        "background": _colour(cell.fill.fgColor) if cell.fill.patternType == "solid" else None,
        "color": _colour(cell.font.color),
        "fontSize": min(_pixels(float(cell.font.sz), 4 / 3, 0), 100) if cell.font.sz else None,
        "bold": cell.font.b,
        "italic": cell.font.i,
        "underline": bool(cell.font.u),
        "wrap": bool(cell.alignment.wrap_text),
        "align": cell.alignment.horizontal,
        "vertical": cell.alignment.vertical,
        "border": [
            bool(getattr(cell.border, name) and getattr(cell.border, name).style)
            for name in ("top", "right", "bottom", "left")
        ],
    }


def _display(value: Any, fmt: str) -> str:
    if isinstance(value, date | time | timedelta):
        return str(value)
    if isinstance(value, int | float) and not isinstance(value, bool):
        # An invalid or enormous custom format shouldn't hide the worksheet.
        try:
            return displayed_text(value, fmt[:200])
        except (ArithmeticError, ValueError):
            return str(value)
    return displayed_text(value)


def _cells(sheet: Any, cached: dict[tuple[int, int], Any]) -> tuple[list[Any], dict[int, Any]]:
    cells: list[Any] = []
    styles: dict[int, Any] = {}
    text_left = 6 * 1024 * 1024
    for cell in sheet._cells.values():
        if cell.row > _MAX_ROWS or cell.column > _MAX_COLUMNS:
            continue
        if cell.value is None and not cell.has_style:
            continue
        if len(cells) >= _MAX_CELLS:
            raise WorkbookTooLarge
        raw = cell.value
        formula = raw if isinstance(raw, str) else getattr(raw, "text", None)
        if cell.data_type != "f":
            formula = None
        value = cached.get((cell.row, cell.column)) if cell.data_type == "f" else raw
        shown = _display(value, cell.number_format)[:32_767]
        raw_text = str(value)[:32_767] if value is not None else ""
        text_left -= len(shown) + len(formula or raw_text)
        if text_left < 0:
            raise WorkbookTooLarge
        style_id = cell.style_id
        if style_id and style_id not in styles:
            styles[style_id] = _style(cell)
        cells.append(
            [
                cell.row,
                cell.column,
                shown,
                formula or raw_text,
                style_id,
                isinstance(value, int | float | date | time | timedelta)
                and not isinstance(value, bool),
            ]
        )
    return cells, styles


def _pixels(value: float, scale: float, extra: int) -> int:
    return min(2000, max(1, round(value * scale + extra))) if math.isfinite(value) else 24


def _dimensions(sheet: Any) -> dict[str, Any]:
    freeze = coordinate_to_tuple(sheet.freeze_panes) if sheet.freeze_panes else (1, 1)
    return {
        "rowCount": min(sheet.max_row, _MAX_ROWS),
        "columnCount": min(sheet.max_column, _MAX_COLUMNS),
        "rowsClipped": sheet.max_row > _MAX_ROWS,
        "freeze": [min(freeze[0] - 1, _MAX_ROWS), min(freeze[1] - 1, _MAX_COLUMNS)],
        "rowHeight": _pixels(sheet.sheet_format.defaultRowHeight or 18, 4 / 3, 0),
        "columnWidth": _pixels(sheet.sheet_format.defaultColWidth or 13, 7, 5),
        "rows": [
            [i, i, 0 if dim.hidden else _pixels(dim.height, 4 / 3, 0)]
            for i, dim in sheet.row_dimensions.items()
            if dim.hidden or dim.height is not None
        ],
        "columns": [
            [
                dim.min or column_index_from_string(key),
                dim.max or column_index_from_string(key),
                0 if dim.hidden else _pixels(dim.width, 7, 5),
            ]
            for key, dim in sheet.column_dimensions.items()
        ],
        "merges": [
            [area.min_row, area.min_col, min(area.max_row, _MAX_ROWS), area.max_col]
            for area in sheet.merged_cells.ranges
            if area.min_row <= _MAX_ROWS
        ],
    }


def read_spreadsheet(path: Path, name: str | None) -> dict[str, Any]:
    with path.open("rb") as stream:
        _check_size(stream)
        workbook = load_workbook(stream, keep_links=False)
        try:
            sheets = [ws.title for ws in workbook.worksheets if ws.sheet_state == "visible"]
            if not sheets or (name is not None and name not in sheets):
                return {"sheets": sheets, "sheet": None}
            active = getattr(workbook.active, "title", None)
            sheet = workbook[name or (active if active in sheets else sheets[0])]
            stream.seek(0)
            values = load_workbook(stream, data_only=True, keep_links=False)
            try:
                cached = {
                    key: {
                        coord: cell.value
                        for coord, cell in values[key]._cells.items()
                        if cell.value is not None
                    }
                    for key in chart_references(sheet) | {sheet.title}
                    if key in values and hasattr(values[key], "_cells")
                }
                cells, styles = _cells(sheet, cached[sheet.title])
                return {
                    "sheets": sheets,
                    "sheet": {
                        "name": sheet.title,
                        **_dimensions(sheet),
                        "cells": cells,
                        "styles": styles,
                        "drawings": drawings(sheet, cached),
                    },
                }
            finally:
                values.close()
        finally:
            workbook.close()
