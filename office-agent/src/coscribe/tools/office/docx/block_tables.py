"""What a table looks like for the Docs editor: widths, borders, cell fills and the look of each
cell's text. A table the editor can change carries it beside its rows; one it cannot change
(merged cells, several paragraphs in a cell) is sent whole, to be drawn and kept as it is."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .look import Looks

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_MAX_CELLS = 400

ReadRuns = Callable[[Any, Any, Looks, dict[str, Any]], list[dict[str, Any]]]


def _q(name: str) -> str:
    return f"{{{_W}}}{name}"


def _height(row: Any) -> float | None:
    height = row.find(f"{_q('trPr')}/{_q('trHeight')}")
    value = height.get(_q("val")) if height is not None else None
    return round(int(value) / 20, 2) if value and value.isdigit() else None


def _shape(table: Any, looks: Looks) -> dict[str, Any]:
    widths, edges = looks.table_widths(table), looks.table_edges(table)
    return {**({"widths": widths} if widths else {}), **({"edges": edges} if edges else {})}


def editable_look(table: Any, looks: Looks, links: Any, read_runs: ReadRuns) -> dict[str, Any]:
    """The look of a table the editor can change, with each cell's own fill and text look."""
    rows = []
    for row in table.findall(_q("tr")):
        cells = []
        for cell in row.findall(_q("tc")):
            paragraph = cell.find(_q("p"))
            cells.append({"look": looks.cell(cell), "p": looks.paragraph(paragraph)})
        height = _height(row)
        rows.append({**({"h": height} if height else {}), "cells": cells})
    return {**_shape(table, looks), "rows": rows}


def _spans(table: Any) -> list[list[int | None]]:
    """Per cell, how many rows a vertical merge starting there covers (None: it continues one)."""
    rows = [row.findall(_q("tc")) for row in table.findall(_q("tr"))]
    spans: list[list[int | None]] = []
    for r, cells in enumerate(rows):
        line: list[int | None] = []
        for c, cell in enumerate(cells):
            merge = cell.find(f"{_q('tcPr')}/{_q('vMerge')}")
            if merge is None:
                line.append(1)
            elif merge.get(_q("val"), "continue") == "continue":
                line.append(None)
            else:
                count = 1
                for below in rows[r + 1 :]:
                    follower = (
                        below[c].find(f"{_q('tcPr')}/{_q('vMerge')}") if c < len(below) else None
                    )
                    if follower is None or follower.get(_q("val"), "continue") != "continue":
                        break
                    count += 1
                line.append(count)
        spans.append(line)
    return spans


def locked_grid(table: Any, looks: Looks, links: Any, read_runs: ReadRuns) -> dict[str, Any]:
    """A table the editor cannot change, cell by cell, so it can be drawn."""
    rows: list[dict[str, Any]] = []
    budget = _MAX_CELLS
    spans = _spans(table)
    for r, row in enumerate(table.findall(_q("tr"))):
        cells: list[dict[str, Any]] = []
        for c, cell in enumerate(row.findall(_q("tc"))):
            if budget <= 0:
                break
            budget -= 1
            if spans[r][c] is None:
                continue
            paragraphs = []
            for paragraph in cell.findall(_q("p")):
                look = looks.paragraph(paragraph)
                paragraphs.append(
                    {
                        "runs": read_runs(paragraph, links, looks, look),
                        **({"look": look} if look else {}),
                    }
                )
            entry: dict[str, Any] = {"paras": paragraphs}
            if look := looks.cell(cell):
                entry["look"] = look
            span = cell.find(f"{_q('tcPr')}/{_q('gridSpan')}")
            value = span.get(_q("val")) if span is not None else None
            if value and value.isdigit() and int(value) > 1:
                entry["span"] = int(value)
            if (down := spans[r][c]) and down > 1:
                entry["down"] = down
            cells.append(entry)
        height = _height(row)
        rows.append({**({"h": height} if height else {}), "cells": cells})
    return {**_shape(table, looks), "rows": rows}


def component_of(element: Any) -> str | None:
    """The spec component that wrote a block (decision 0024), from the `cs_` bookmark the compiler
    leaves in it: `stats`, `callout_warn`, `chart`... None for anything else."""
    for start in element.iter(_q("bookmarkStart")):
        name = start.get(_q("name")) or ""
        if name.startswith("cs_"):
            return name[3:]
    return None
