"""Pipe-table row helpers shared by the documents, spreadsheets and chart tools."""

from __future__ import annotations

import re

_SEPARATOR_CELL_RE = re.compile(r"^:?-{2,}:?$")


def _split_table_row(line: str) -> list[str] | None:
    if not (line.startswith("|") and line.endswith("|") and len(line) >= 2):
        return None
    return [cell.strip() for cell in line[1:-1].split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    return all(_SEPARATOR_CELL_RE.match(cell) for cell in cells)
