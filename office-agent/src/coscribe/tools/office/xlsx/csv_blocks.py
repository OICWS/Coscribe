"""`write_xlsx_cells`' `from_csv`: a CSV file of the workspace copied into a block, so a large
table is never retyped by the model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..._workspace import WorkspaceScope
from .helpers import _coerce_cell

_CSV_ROWS = 100_000


def _csv_value(value: str) -> Any:
    """Numbers as numbers; text stays text, including text that starts with `=`: a downloaded
    file's cell is data, never a formula to run."""
    if not value.strip():
        return None
    if value.startswith("="):
        return {"v": value, "text": True}
    return _coerce_cell(value)


def _csv_lines(path: Path) -> list[str]:
    """The file's text: UTF-8, or GB18030 as Excel saves a CSV on a Chinese system."""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return raw.decode("gb18030").splitlines()


def _csv_rows(scope: WorkspaceScope, name: Any) -> list[list[Any]]:
    """A CSV file's rows, blank lines kept so row offsets match the file."""
    import csv

    if not isinstance(name, str) or not name:
        raise ValueError("`from_csv` is the path of a CSV file in the workspace")
    rows: list[list[Any]] = []
    for row in csv.reader(_csv_lines(scope.resolve(name))):
        if len(rows) == _CSV_ROWS:
            raise ValueError(f"{name} has more than {_CSV_ROWS} rows, more than a block takes")
        rows.append([_csv_value(value) for value in row])
    while rows and not any(v is not None for v in rows[-1]):
        rows.pop()
    return rows


def expand_blocks(scope: WorkspaceScope, blocks: Any) -> Any:
    """The blocks with each `from_csv` replaced by the CSV file's rows."""
    if not isinstance(blocks, list):
        return blocks
    expanded = []
    for i, block in enumerate(blocks):
        if isinstance(block, dict) and "from_csv" in block:
            if "rows" in block:
                raise ValueError(f"blocks[{i}]: give `rows` or `from_csv`, not both")
            rest = {k: v for k, v in block.items() if k != "from_csv"}
            block = {**rest, "rows": _csv_rows(scope, block["from_csv"])}
        expanded.append(block)
    return expanded
