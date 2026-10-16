from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Optional

from ....runtime import tool_metadata
from ..._output_truncation import cap_read_output
from .toolkit import SpreadsheetToolkit


def build_spreadsheet_tools(
    root: str | Path,
    *,
    state_dir: str | Path | None = None,
    extra_readable: Sequence[str | Path] = (),
    extra_writable: Sequence[str | Path] = (),
) -> list[Callable[..., Any]]:
    """Return the tool callables the Coordinator agent can call, bound to `root`
    (plus any user-configured extra_readable/extra_writable directories)."""
    toolkit = SpreadsheetToolkit(
        root, state_dir=state_dir, extra_readable=extra_readable, extra_writable=extra_writable
    )

    # `Optional[str]`, not `str | None`: aisuite's Tools.__infer_from_signature
    # only unwraps typing.Optional (checks `get_origin(t) is Union`), and PEP
    # 604 `X | None` has origin `types.UnionType` instead -- it slips through
    # unwrapped and gets serialized as the literal string "str | None" for
    # the "type" field, which Gemini's strict OpenAPI-subset schema rejects.
    def read_xlsx(path: str, sheet: Optional[str] = None) -> str:  # noqa: UP045
        """Read an Excel (.xlsx) file under the workspace as markdown tables.

        Without `sheet`, every sheet is rendered as a `## <sheet name>`
        heading followed by its table -- a full workbook overview in one
        call. With `sheet`, only that sheet's table is rendered (no
        heading) -- use this to avoid spending context on sheets you don't
        need in a workbook with many/large sheets.

        Args:
            path: file to read, relative to the workspace root
            sheet: sheet name to read; omit to read every sheet
        """
        return cap_read_output(
            toolkit.read_xlsx(path=path, sheet=sheet),
            "read one sheet with the sheet argument; to count, filter or total a large "
            "sheet, use a script with pandas instead of reading it",
        )

    def recalc_xlsx(path: str) -> dict[str, object]:
        """Recalculate every formula in an existing Excel (.xlsx) file and
        write the computed values into it.

        write_xlsx_cells and modify_xlsx already do this after every
        write, so you don't need to call this after them. Use it for a
        file that already has formulas but wasn't written by them (e.g.
        one the user attached), or to re-verify a workbook you've since
        edited some other way.

        `status` in the response is `"success"`, `"errors_found"` (fix the
        cells `error_locations` names and recalc again), or `"skipped"`
        (the formula engine could not read the workbook -- see
        `skipped_reason`).

        Args:
            path: file to recalculate, relative to the workspace root
        """
        return toolkit.recalc_xlsx(path=path)

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
        return toolkit.write_xlsx_cells(
            path=path, blocks=blocks, styles=styles, overwrite=overwrite
        )

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
        return toolkit.modify_xlsx(path=path, ops=ops)

    return [
        tool_metadata(read_xlsx, risk_category="READ", category="documents"),
        tool_metadata(recalc_xlsx, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(write_xlsx_cells, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(modify_xlsx, risk_category="WRITE_LOCAL", category="documents"),
    ]
