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

    def write_xlsx(
        path: str, content: str, sheet_name: str = "Sheet1", overwrite: bool = True
    ) -> dict[str, object]:
        """Create or update one sheet of an Excel (.xlsx) file under the workspace.

        `content` is pipe-table rows only (`| cell | cell |`, one row per
        line) -- a spreadsheet is a grid, not flowing text, so headings/
        bullets/paragraphs don't apply here like they do for write_docx/
        write_pdf. Cells that look numeric are stored as real numbers
        (usable in Excel formulas), not text.

        A cell starting with `=` is written as a real Excel formula, e.g.
        `=SUM(B2:B9)` -- prefer this over writing a pre-computed number
        whenever the value depends on other cells, so the sheet actually
        recalculates when its inputs change. Reference other cells by
        their real address (`=B5*1.05`, not a hardcoded number); use
        `INDEX`/`MATCH` for lookups, not `XLOOKUP`, which this tool
        rejects outright (it can't be verified -- see below). If a formula
        needs to reference a cell outside this call's own `content` (e.g.
        an earlier sheet), write this sheet first, then chain another
        write_xlsx call with formulas referencing it.

        After writing, if the sheet contains any formulas, this
        automatically recalculates them and writes the values into the
        file (openpyxl itself only writes the formula text, no cached
        value), and checks for Excel error strings (`#DIV/0!` etc.)
        -- see the response's `recalc_status`/`total_errors`/
        `formula_error_locations`. `recalc_status: "errors_found"` means
        ship nothing yet: fix the formulas the errors point at and call
        write_xlsx again. A clean recalc proves the formulas *evaluate*,
        not that they're *right* -- double-check a couple of cells against
        what you expect before building out a large grid.

        Unlike write_docx/write_pdf, `overwrite` is scoped to this sheet,
        not the whole file: writing a new `sheet_name` to an existing file
        always appends it (build up a multi-sheet workbook with repeated
        calls); writing an existing `sheet_name` replaces its content only
        if `overwrite=True`, otherwise raises.

        The response's `preview_path` (when the file can be drawn) names
        a rendered thumbnail of `sheet_name` the user can see in the chat
        UI -- not something to fetch or parse yourself.

        Args:
            path: file to write, relative to the workspace root
            content: pipe-table rows for this sheet
            sheet_name: sheet to create or replace
            overwrite: whether to replace `sheet_name` if it already exists
        """
        return toolkit.write_xlsx(
            path=path, content=content, sheet_name=sheet_name, overwrite=overwrite
        )

    def recalc_xlsx(path: str) -> dict[str, object]:
        """Recalculate every formula in an existing Excel (.xlsx) file and
        write the computed values into it.

        write_xlsx already does this automatically whenever it writes a
        formula, so you don't need to call this after write_xlsx. Use it
        for a file that already has formulas but wasn't written by
        write_xlsx (e.g. one the user attached), or to re-verify a
        workbook you've since edited some other way.

        `status` in the response is `"success"`, `"errors_found"` (fix the
        cells `error_locations` names and recalc again), or `"skipped"`
        (the formula engine could not read the workbook -- see
        `skipped_reason`).

        Args:
            path: file to recalculate, relative to the workspace root
        """
        return toolkit.recalc_xlsx(path=path)

    def format_xlsx_cells(
        path: str,
        sheet_name: str,
        cell_range: str,
        number_format: str = "",
        font_color: str = "",
        bold: bool = False,
    ) -> dict[str, object]:
        """Apply a number format and/or font color/weight to a cell range
        in an existing Excel (.xlsx) file.

        `cell_range` is a single cell (`"B2"`) or a range (`"B2:D10"`).
        `number_format` is an Excel format code -- common ones: currency
        `"$#,##0"`, percentage `"0.0%"` (store the value as a fraction,
        e.g. 0.15 for 15%, not 15), `"$#,##0;($#,##0);-"` for negatives in
        parentheses and zeros as a dash, `"0.0x"` for a valuation
        multiple. `font_color` is a 6-digit hex RGB string with no `#`
        (e.g. `"FF0000"` for red). For a financial model, the common
        convention is blue text for hardcoded inputs/assumptions, black
        (leave `font_color` empty) for formulas, green for links to
        another sheet -- apply it if you're building one and the user
        hasn't specified their own convention.

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet containing the range
            cell_range: cell or range to format, e.g. "B2" or "B2:D10"
            number_format: Excel number format code; omit to leave as-is
            font_color: 6-digit hex RGB color with no `#`; omit to leave as-is
            bold: whether to make the range bold
        """
        return toolkit.format_xlsx_cells(
            path=path,
            sheet_name=sheet_name,
            cell_range=cell_range,
            number_format=number_format,
            font_color=font_color,
            bold=bold,
        )

    def add_xlsx_chart(
        path: str,
        sheet_name: str,
        chart_type: str,
        data_range: str = "",
        title: str = "",
        anchor: str = "",
    ) -> dict[str, object]:
        """Add a chart to an existing Excel (.xlsx) file, reading data already in the sheet.

        Omit `data_range` to chart the sheet's entire used range -- the
        common case, and safer than naming it yourself: get a row or column
        wrong and the chart silently drops real data or plots a phantom
        empty series. Only pass `data_range` when you specifically want a
        subset of a larger sheet, as A1 notation covering a header row plus
        the data rows (e.g. `"A1:C6"`). Either way: the first column is the
        category axis; every other column becomes its own data series,
        named from that column's header cell. `chart_type` is `"bar"`,
        `"line"`, or `"pie"` -- a pie chart takes exactly one data column (a
        second series has no meaningful rendering as pie slices).

        The response's `preview_path` (when the file can be drawn) names
        a rendered thumbnail the user can see in the chat UI -- not
        something to fetch or parse yourself.

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet the data (and the new chart) live in
            chart_type: "bar", "line", or "pie"
            data_range: A1 range including the header row, e.g. "A1:C6";
                omit to use the sheet's entire used range
            title: optional chart title
            anchor: cell the chart's top-left corner anchors to, e.g. "E2";
                omit to place it just right of the charted range
        """
        return toolkit.add_xlsx_chart(
            path=path,
            sheet_name=sheet_name,
            chart_type=chart_type,
            data_range=data_range,
            title=title,
            anchor=anchor,
        )

    def merge_xlsx_cells(path: str, sheet_name: str, cell_range: str) -> dict[str, object]:
        """Merge a cell range in an existing Excel (.xlsx) file into one cell.

        Only the top-left cell of `cell_range` keeps its value/formatting
        after merging -- write to that cell (e.g. with `edit_xlsx_cells`)
        before or after merging, not any other cell in the range, which
        openpyxl makes read-only once merged. Rejects a range that
        overlaps a merge that already exists on the sheet.

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet containing the range
            cell_range: range to merge, e.g. "A1:C1"
        """
        return toolkit.merge_xlsx_cells(path=path, sheet_name=sheet_name, cell_range=cell_range)

    def unmerge_xlsx_cells(path: str, sheet_name: str, cell_range: str) -> dict[str, object]:
        """Undo a merge in an existing Excel (.xlsx) file, restoring individual cells.

        `cell_range` must exactly match a range that's currently merged
        (e.g. what `merge_xlsx_cells` was called with) -- raises if it
        isn't currently merged.

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet containing the range
            cell_range: the exact currently-merged range to undo, e.g. "A1:C1"
        """
        return toolkit.unmerge_xlsx_cells(path=path, sheet_name=sheet_name, cell_range=cell_range)

    def add_xlsx_conditional_format(
        path: str,
        sheet_name: str,
        cell_range: str,
        rule_type: str,
        operator: str = "",
        formula: str = "",
        fill_color: str = "",
        min_color: str = "",
        mid_color: str = "",
        max_color: str = "",
    ) -> dict[str, object]:
        """Add conditional formatting to a cell range in an existing Excel (.xlsx) file.

        `rule_type` is one of:
        - `"cell_is"`: highlights cells that satisfy a comparison. Needs
          `operator` (`">"`, `"<"`, `">="`, `"<="`, `"="`, `"!="`, or
          `"between"`/`"notBetween"`) and `formula` (the comparison
          value, e.g. `"0"`; for `"between"`/`"notBetween"`, two values
          separated by a comma, e.g. `"10,20"`) and `fill_color`.
        - `"color_scale"`: a gradient from `min_color` to `max_color`
          (both required) across the range's actual min/max values;
          `mid_color` optionally adds a third stop at the median.
        - `"data_bar"`: an in-cell bar proportional to each cell's value
          relative to the range's min/max, filled with `fill_color`.

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet containing the range
            cell_range: range the rule applies to, e.g. "B2:B20"
            rule_type: "cell_is", "color_scale", or "data_bar"
            operator: comparison operator, for "cell_is" only
            formula: comparison value(s), for "cell_is" only
            fill_color: 6-digit hex RGB with no "#", for "cell_is"/"data_bar"
            min_color: 6-digit hex RGB with no "#", for "color_scale"
            mid_color: 6-digit hex RGB with no "#", optional, for "color_scale"
            max_color: 6-digit hex RGB with no "#", for "color_scale"
        """
        return toolkit.add_xlsx_conditional_format(
            path=path,
            sheet_name=sheet_name,
            cell_range=cell_range,
            rule_type=rule_type,
            operator=operator,
            formula=formula,
            fill_color=fill_color,
            min_color=min_color,
            mid_color=mid_color,
            max_color=max_color,
        )

    def set_xlsx_data_validation(
        path: str,
        sheet_name: str,
        cell_range: str,
        validation_type: str,
        formula1: str,
        formula2: str = "",
        operator: str = "between",
        allow_blank: bool = True,
        error_message: str = "",
        error_title: str = "",
    ) -> dict[str, object]:
        """Restrict what can be entered into a cell range in an existing Excel (.xlsx) file.

        `validation_type` is `"list"` (a dropdown -- `formula1` is either
        a plain comma-separated list of options, e.g. `"Yes,No,Maybe"`,
        or a range reference, e.g. `"$D$1:$D$5"`), `"whole"`/`"decimal"`
        (numeric range, using `operator` and `formula1`/`formula2`,
        e.g. operator `"between"` with formula1/formula2 as the bounds),
        `"date"`/`"time"` (same, with date/time values), `"textLength"`
        (character count), or `"custom"` (an arbitrary formula in
        `formula1` that must evaluate to TRUE).

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet containing the range
            cell_range: range the validation applies to, e.g. "B2:B20"
            validation_type: "list", "whole", "decimal", "date", "time",
                "textLength", or "custom"
            formula1: the option list/range/bound/formula -- meaning
                depends on validation_type, see above
            formula2: second bound, for "between"/"notBetween" operators
                on numeric/date/time types
            operator: "between", "notBetween", "equal", "notEqual",
                "lessThan", "lessThanOrEqual", "greaterThan", or
                "greaterThanOrEqual" -- ignored for "list"/"custom"
            allow_blank: whether an empty cell is considered valid
            error_message: message shown when an invalid value is entered;
                omit for no error popup at all
            error_title: title of the error popup, when error_message is set
        """
        return toolkit.set_xlsx_data_validation(
            path=path,
            sheet_name=sheet_name,
            cell_range=cell_range,
            validation_type=validation_type,
            formula1=formula1,
            formula2=formula2,
            operator=operator,
            allow_blank=allow_blank,
            error_message=error_message,
            error_title=error_title,
        )

    def freeze_xlsx_panes(path: str, sheet_name: str, cell: str = "") -> dict[str, object]:
        """Freeze rows/columns above and left of `cell` in an existing Excel (.xlsx) file.

        E.g. `cell="B2"` freezes row 1 and column A so they stay visible
        while scrolling; `cell="A3"` freezes just the first two rows;
        `cell="C1"` freezes just the first two columns. Omit `cell` (or
        pass `"A1"`) to remove any existing freeze.

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet to freeze panes on
            cell: the first scrollable cell, e.g. "B2"; omit to unfreeze
        """
        return toolkit.freeze_xlsx_panes(path=path, sheet_name=sheet_name, cell=cell)

    def set_xlsx_column_width(
        path: str, sheet_name: str, columns: str, width: float
    ) -> dict[str, object]:
        """Set column width(s) in an existing Excel (.xlsx) file.

        `width` is in Excel's own character-width units (roughly the
        number of digits of the default font that fit -- 8.43 is Excel's
        own default; wide text columns commonly want 20-40).

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet containing the column(s)
            columns: a single column letter (e.g. "B") or a range (e.g. "B:D")
            width: column width to set
        """
        return toolkit.set_xlsx_column_width(
            path=path, sheet_name=sheet_name, columns=columns, width=width
        )

    def edit_xlsx_cells(
        path: str, sheet_name: str, start_cell: str, content: str
    ) -> dict[str, object]:
        """Write a block of cells into an existing sheet, leaving everything else untouched.

        Unlike `write_xlsx` (which replaces the *entire* named sheet's
        content), this only touches the cells `content` actually covers,
        starting at `start_cell` -- other cells, formatting, merged
        ranges, and charts on the sheet are left exactly as they were.
        Use this to fix or update a few cells in a sheet that already has
        real structure you don't want to lose.

        `content` uses the same pipe-table syntax as `write_xlsx`
        (`| cell | cell |`, one row per line) -- a single cell is just one
        row with one column, e.g. `"| 42 |"`. Cells that look numeric
        become real numbers; a cell starting with `=` becomes a real
        formula, validated/auto-corrected the same way `write_xlsx` does
        (rejecting `XLOOKUP`-class functions, `_xlfn.`-prefixing post-2007
        functions). If any formula is written, this automatically
        recalculates the workbook the same way `write_xlsx`
        does -- see the response's `recalc_status`/`total_errors`.

        The response's `preview_path` (when the file can be drawn) names
        a rendered thumbnail of `sheet_name` the user can see in the chat
        UI -- not something to fetch or parse yourself.

        Args:
            path: file to modify, relative to the workspace root
            sheet_name: sheet to edit -- must already exist
            start_cell: top-left cell of the block to write, e.g. "B3"
            content: pipe-table rows to write starting at start_cell
        """
        return toolkit.edit_xlsx_cells(
            path=path, sheet_name=sheet_name, start_cell=start_cell, content=content
        )

    return [
        tool_metadata(read_xlsx, risk_category="READ", category="documents"),
        tool_metadata(write_xlsx, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(recalc_xlsx, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(format_xlsx_cells, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(add_xlsx_chart, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(merge_xlsx_cells, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(unmerge_xlsx_cells, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(
            add_xlsx_conditional_format, risk_category="WRITE_LOCAL", category="documents"
        ),
        tool_metadata(
            set_xlsx_data_validation, risk_category="WRITE_LOCAL", category="documents"
        ),
        tool_metadata(freeze_xlsx_panes, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(set_xlsx_column_width, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(edit_xlsx_cells, risk_category="WRITE_LOCAL", category="documents"),
    ]
