"""`write_xlsx_cells` and `modify_xlsx`: the block and object operations as the agent's tools
(decision 0011). The operations' contract lives in these descriptions, which are static (0001)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ....runtime import tool_metadata
from ..._file_locks import file_lock
from ..._workspace import WorkspaceScope
from .build import modify_workbook, write_cells
from .helpers import _coerce_cell

_CSV_ROWS = 100_000


def _relative(scope: WorkspaceScope, report: dict[str, Any]) -> dict[str, Any]:
    return {**report, "path": scope.relative(Path(report["path"]))}


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


def _expand(scope: WorkspaceScope, blocks: Any) -> Any:
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


def build_block_tools(
    root: str | Path,
    *,
    extra_readable: Sequence[str | Path] = (),
    extra_writable: Sequence[str | Path] = (),
) -> list[Callable[..., Any]]:
    scope = WorkspaceScope(root, extra_readable=extra_readable, extra_writable=extra_writable)

    def write_xlsx_cells(
        path: str,
        blocks: list[dict[str, Any]],
        styles: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Write blocks of cells, with their styles, into an Excel workbook (created if missing).

        Write a whole table, or a whole workbook, in one call: every block in `blocks` is written,
        then the workbook is recalculated and checked.

        A block: {"sheet": "Summary", "at": "A1", "rows": [[...], [...]], ...}
        - rows: a list of rows; a cell is a number, text, true/false, null (left empty), a
          formula "=SUM(B2:B9)", or {"v": value | "f": "=formula", "s": style, "note": "...",
          "text": true (the value as written, never a formula or a date)}.
          Text written as 2026-01-05 (or 2026-01-05 14:30) becomes a real date.
        - style / row_styles / col_styles: a style for the block, by row or by column position
          (a list, or {"0": style}); a cell's own "s" wins, then the row's, then the column's.
        - like: "C2" gives every cell the look of that cell; like_row: 7 gives each cell the look
          of its own column in row 7. Use one when adding to a table the user already has.
        - fill_down_to: 20 repeats the block's last row down to row 20, formulas moved with it.
        - from_csv: "data.csv" instead of rows copies a CSV file of the workspace, numbers as
          numbers: a large table is never retyped.
        A sheet that does not exist is created.

        A style is a name defined in `styles` ({"head": {...}}) or inline: bold, italic,
        underline, wrap (true/false), color and fill ("1F3864"), font, size, num (a number
        format: "#,##0", "0.0%", "yyyy-mm-dd", '#,##0"元"'), align (left/center/right),
        valign (top/center/bottom), indent, border ("thin", or {"bottom": "medium"}).

        Results are formulas over the inputs, never numbers you computed. Cells that already hold
        something else are not written over unless overwrite is true; the refusal names them.

        Returns `formula_results` (each formula written and the value it computed: check them),
        `recalc` (formula errors), and `findings` by cell: fix them with another call. A user's
        workbook that would lose something openpyxl cannot keep is saved as "<name>
        (coscribe).xlsx" instead (`saved_as_copy`, `lost_if_saved_over_original`): tell the user.

        Args:
            path: the .xlsx file, relative to the workspace root
            blocks: the blocks to write, as described above
            styles: named styles the blocks refer to
            overwrite: write over cells that hold something else
        """
        file_path = scope.resolve(path, write=True)
        with file_lock(file_path):
            report = write_cells(file_path, _expand(scope, blocks), styles, overwrite)
            return _relative(scope, report)

    def modify_xlsx(path: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
        """Change a workbook's sheets, layout and objects: charts, rules, lists, print setup.

        `ops` is a list, applied in order, of:
        - {"op": "add_sheet", "name", "index"?, "tab_color"?}, {"op": "rename_sheet", "sheet",
          "name"}, {"op": "delete_sheet", "sheet"}, {"op": "tab_color", "sheet", "color"}
        - {"op": "cols", "sheet", "cols": "B:D", "width"?, "hidden"?}, {"op": "rows", "sheet",
          "rows": "1:2", "height"?, "hidden"?}
        - {"op": "freeze", "sheet", "at": "A2"} (no "at" unfreezes), {"op": "merge", "sheet",
          "range": "A1:D1", "undo"?}
        - {"op": "chart", "sheet", "kind": column|bar|line|pie|area|scatter, "source": "A1:C13"
          or "Data!A1:C13", "at": "E2", "title"?, "x_title"?, "y_title"?, "colors"?: [hex per
          series], "stacked"?, "labels"?, "size"?: [width_cm, height_cm]}. The source's first row
          names the series and its first column holds the categories. Place a chart beside its
          table, not over it.
        - {"op": "conditional", "sheet", "range", "rule": color_scale|data_bar|cell|formula|top,
          "colors"?, "operator"? (greaterThan, lessThan, between, equal...), "values"?,
          "formula"?, "fill"?, "color"?, "rank"?}
        - {"op": "validation", "sheet", "range", "list": ["Open", "Done"] or
          "source": "=Lists!A1:A5", "message"?}
        - {"op": "print", "sheet", "landscape"?, "fit_width"?: 1, "repeat_rows"?: "1:1",
          "area"?}
        - {"op": "name", "name", "ref": "Sheet1!$B$2:$B$9"}

        Returns the same `recalc` and `findings` as write_xlsx_cells, with the same rule for a
        user's workbook that would lose something.

        Args:
            path: the .xlsx file, relative to the workspace root
            ops: the operations, as described above
        """
        file_path = scope.resolve(path, write=True)
        with file_lock(file_path):
            return _relative(scope, modify_workbook(file_path, ops))

    return [
        tool_metadata(write_xlsx_cells, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(modify_xlsx, risk_category="WRITE_LOCAL", category="documents"),
    ]
