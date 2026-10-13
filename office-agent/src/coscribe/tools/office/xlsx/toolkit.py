from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

from ..._file_locks import locked_by_path
from ..._thumbnail import render_thumbnail
from ..._workspace import WorkspaceScope
from .helpers import (
    _CHART_TYPES,
    _CONDITIONAL_FORMAT_RULE_TYPES,
    _DATA_VALIDATION_TYPES,
    _XLSX_RECALC_TIMEOUT,
    _coerce_cell,
    _parse_table_rows,
    _recalc_xlsx_and_evaluate_lookups,
    _render_sheet_table,
    _workbook_has_any_formula,
)


class SpreadsheetToolkit:
    def __init__(
        self,
        root: str | Path,
        *,
        state_dir: str | Path | None = None,
        extra_readable: Sequence[str | Path] = (),
        extra_writable: Sequence[str | Path] = (),
    ) -> None:
        self._scope = WorkspaceScope(
            root, extra_readable=extra_readable, extra_writable=extra_writable
        )
        self._state_dir = Path(state_dir) if state_dir is not None else None

    def _check_readable(self, path: str) -> Path:
        file_path = self._scope.resolve(path)
        if not file_path.exists():
            raise ValueError(f"File does not exist: {path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        return file_path

    def _check_writable(self, path: str) -> Path:
        file_path = self._scope.resolve(path, write=True)
        if file_path.exists() and file_path.is_dir():
            raise ValueError(f"Path is a directory: {path}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    def _check_editable(self, path: str) -> Path:
        """Like `_check_writable`, but requires the file to already exist --
        for tools that edit an existing workbook in place (merge/format/
        validation/etc.) rather than creating one, matching the same
        write-scoped-and-must-already-exist contract `office/docx`'s
        `_check_editable` uses for its own tracked-edit tools."""
        file_path = self._scope.resolve(path, write=True)
        if not file_path.exists():
            raise ValueError(f"File does not exist: {path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        return file_path

    @locked_by_path
    def read_xlsx(self, path: str, sheet: Optional[str] = None) -> str:  # noqa: UP045
        from openpyxl import load_workbook

        file_path = self._check_readable(path)
        workbook = load_workbook(str(file_path), data_only=True)
        if sheet is not None:
            if sheet not in workbook.sheetnames:
                raise ValueError(
                    f"Sheet {sheet!r} not found. Available sheets: {workbook.sheetnames}"
                )
            return _render_sheet_table(workbook[sheet])
        sections = []
        for name in workbook.sheetnames:
            sections.append(f"## {name}\n\n{_render_sheet_table(workbook[name])}")
        return "\n\n".join(sections)

    @locked_by_path
    def write_xlsx(
        self, path: str, content: str, sheet_name: str = "Sheet1", overwrite: bool = True
    ) -> dict[str, object]:
        from openpyxl import Workbook, load_workbook

        rows = _parse_table_rows(content)
        file_path = self._check_writable(path)
        if file_path.exists():
            workbook = load_workbook(str(file_path))
            if sheet_name in workbook.sheetnames:
                if not overwrite:
                    raise FileExistsError(f"Sheet already exists: {sheet_name}")
                del workbook[sheet_name]
                sheet = workbook.create_sheet(sheet_name)
            else:
                sheet = workbook.create_sheet(sheet_name)
        else:
            workbook = Workbook()
            default_sheet = workbook.active
            sheet = workbook.create_sheet(sheet_name)
            if default_sheet is not None:
                workbook.remove(default_sheet)
        for row in rows:
            sheet.append([_coerce_cell(cell) for cell in row])
        # Makes the just-written sheet the one LibreOffice renders for the
        # preview thumbnail below (and the one Excel opens to) -- without
        # this, amending an existing workbook leaves whatever sheet was
        # already active, which usually isn't sheet_name.
        workbook.active = workbook.index(sheet)
        has_formula = _workbook_has_any_formula(workbook)
        workbook.save(str(file_path))

        recalc_result: dict[str, object] = {"status": "skipped", "skipped_reason": None}
        if has_formula:
            recalc_result = _recalc_xlsx_and_evaluate_lookups(file_path)

        preview_path, preview_skipped_reason = render_thumbnail(file_path, self._state_dir)
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "bytes_written": file_path.stat().st_size,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
            "recalc_status": recalc_result["status"],
            "recalc_skipped_reason": recalc_result.get("skipped_reason"),
            "total_formulas": recalc_result.get("total_formulas"),
            "total_errors": recalc_result.get("total_errors"),
            "formula_error_locations": recalc_result.get("error_locations"),
        }

    @locked_by_path
    def recalc_xlsx(self, path: str, timeout: float = _XLSX_RECALC_TIMEOUT) -> dict[str, object]:
        file_path = self._check_readable(path)
        result = _recalc_xlsx_and_evaluate_lookups(file_path, timeout=timeout)
        return {
            "path": self._scope.relative(file_path),
            "status": result["status"],
            "skipped_reason": result.get("skipped_reason"),
            "total_formulas": result.get("total_formulas"),
            "total_errors": result.get("total_errors"),
            "error_locations": result.get("error_locations"),
        }

    @locked_by_path
    def format_xlsx_cells(
        self,
        path: str,
        sheet_name: str,
        cell_range: str,
        number_format: str = "",
        font_color: str = "",
        bold: bool = False,
    ) -> dict[str, object]:
        from openpyxl import load_workbook
        from openpyxl.styles import Font

        file_path = self._check_readable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]
        try:
            selection = sheet[cell_range]
        except (ValueError, KeyError, IndexError) as exc:
            raise ValueError(f"Invalid cell_range {cell_range!r}: {exc}") from None

        # openpyxl's sheet[range] returns a bare Cell for "A1", a tuple of
        # Cells for "A1:C1", or a tuple of tuples for "A1:C3" -- normalize
        # to a flat list so the loop below doesn't need to branch on shape.
        cells: list[Any]
        if hasattr(selection, "row"):
            cells = [selection]
        else:
            cells = [cell for row in selection for cell in row]

        for cell in cells:
            if number_format:
                cell.number_format = number_format
            if font_color or bold:
                cell.font = Font(
                    name=cell.font.name,
                    size=cell.font.size,
                    bold=bold or cell.font.bold,
                    color=font_color or cell.font.color,
                )
        workbook.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "cell_range": cell_range,
            "cells_formatted": len(cells),
        }

    @locked_by_path
    def add_xlsx_chart(
        self,
        path: str,
        sheet_name: str,
        chart_type: str,
        data_range: str = "",
        title: str = "",
        anchor: str = "",
    ) -> dict[str, object]:
        from openpyxl import load_workbook
        from openpyxl.chart import BarChart, LineChart, PieChart, Reference
        from openpyxl.utils import get_column_letter
        from openpyxl.utils.cell import range_boundaries

        if chart_type not in _CHART_TYPES:
            raise ValueError(
                f"Unknown chart_type {chart_type!r}. Use one of: {', '.join(sorted(_CHART_TYPES))}"
            )

        file_path = self._check_readable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]

        # Defaulting to the sheet's own used range (rather than requiring
        # the caller to compute it) sidesteps a real, live-reproduced
        # failure mode: a model asked to name the range guessed one row too
        # low and one column too wide, silently dropping the first data row
        # and charting a phantom empty series from a column that doesn't
        # exist. openpyxl already tracks the real bounds -- trust those over
        # a guess whenever the caller doesn't have a specific subset in mind.
        range_source = data_range or sheet.dimensions
        try:
            min_col, min_row, max_col, max_row = range_boundaries(range_source)
        except ValueError:
            min_col = min_row = max_col = max_row = None
        if min_col is None or min_row is None or max_col is None or max_row is None:
            raise ValueError(f"Invalid data_range: {data_range!r} -- use A1 notation, e.g. 'A1:C6'")
        if max_col <= min_col:
            raise ValueError(
                "data_range must span at least two columns -- the first is categories, "
                "the rest are data series"
            )
        if max_row <= min_row:
            raise ValueError("data_range must include a header row plus at least one data row")
        # A pie chart's slices are one series' proportions of a whole -- a
        # second series has no meaningful rendering, unlike bar/line where
        # openpyxl's add_data(titles_from_data=True) happily plots several.
        if chart_type == "pie" and max_col - min_col > 1:
            raise ValueError("pie charts take exactly one data column plus the category column")

        chart = {"bar": BarChart, "line": LineChart, "pie": PieChart}[chart_type]()
        if title:
            chart.title = title
        data = Reference(
            sheet, min_col=min_col + 1, min_row=min_row, max_col=max_col, max_row=max_row
        )
        categories = Reference(sheet, min_col=min_col, min_row=min_row + 1, max_row=max_row)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)

        anchor_cell = anchor or f"{get_column_letter(max_col + 2)}{min_row}"
        # `workbook[sheet_name]` is typed as Worksheet | Chartsheet | ... --
        # mypy resolves .add_chart against Chartsheet's narrower signature.
        # We only ever index a name from workbook.sheetnames, which excludes
        # chart sheets in practice for files this package writes.
        sheet.add_chart(chart, anchor_cell)  # type: ignore[call-arg]
        workbook.save(str(file_path))

        preview_path, preview_skipped_reason = render_thumbnail(file_path, self._state_dir)
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "chart_type": chart_type,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def merge_xlsx_cells(self, path: str, sheet_name: str, cell_range: str) -> dict[str, object]:
        from openpyxl import load_workbook
        from openpyxl.worksheet.cell_range import CellRange

        file_path = self._check_editable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]
        try:
            new_range = CellRange(cell_range)
        except ValueError as exc:
            raise ValueError(f"Invalid cell_range {cell_range!r}: {exc}") from None

        # openpyxl's own merge_cells does not check this -- confirmed
        # empirically it silently accepts a second, overlapping merge
        # rather than raising, which real Excel treats as corrupt.
        for existing in sheet.merged_cells.ranges:
            if not new_range.isdisjoint(existing):
                raise ValueError(
                    f"{cell_range!r} overlaps an already-merged range {existing.coord!r}"
                )

        sheet.merge_cells(cell_range)
        workbook.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "cell_range": cell_range,
        }

    @locked_by_path
    def unmerge_xlsx_cells(self, path: str, sheet_name: str, cell_range: str) -> dict[str, object]:
        from openpyxl import load_workbook

        file_path = self._check_editable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]
        try:
            sheet.unmerge_cells(cell_range)
        except (ValueError, KeyError) as exc:
            raise ValueError(f"Cannot unmerge {cell_range!r}: {exc}") from None
        workbook.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "cell_range": cell_range,
        }

    @locked_by_path
    def add_xlsx_conditional_format(
        self,
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
        from openpyxl import load_workbook
        from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
        from openpyxl.styles import PatternFill

        if rule_type not in _CONDITIONAL_FORMAT_RULE_TYPES:
            raise ValueError(
                f"Unknown rule_type {rule_type!r}. Use one of: "
                f"{', '.join(sorted(_CONDITIONAL_FORMAT_RULE_TYPES))}"
            )
        file_path = self._check_editable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]

        # CellIsRule/ColorScaleRule/DataBarRule are plain factory functions
        # in openpyxl (confirmed by reading their source -- no annotations
        # at all, `Rule` is what's actually typed), same reason
        # `add_xlsx_chart`'s own `sheet.add_chart` call above needs its
        # `type: ignore`.
        if rule_type == "cell_is":
            if not operator or not formula:
                raise ValueError("rule_type 'cell_is' requires both operator and formula")
            rule = CellIsRule(  # type: ignore[no-untyped-call]
                operator=operator,
                formula=[part.strip() for part in formula.split(",")],
                fill=PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
                if fill_color
                else None,
            )
        elif rule_type == "color_scale":
            if not min_color or not max_color:
                raise ValueError("rule_type 'color_scale' requires min_color and max_color")
            rule = ColorScaleRule(  # type: ignore[no-untyped-call]
                start_type="min",
                start_color=min_color,
                mid_type="percentile" if mid_color else None,
                mid_value=50 if mid_color else None,
                mid_color=mid_color or None,
                end_type="max",
                end_color=max_color,
            )
        else:  # "data_bar"
            if not fill_color:
                raise ValueError("rule_type 'data_bar' requires fill_color")
            rule = DataBarRule(  # type: ignore[no-untyped-call]
                start_type="min", end_type="max", color=fill_color, showValue=True
            )

        sheet.conditional_formatting.add(cell_range, rule)
        workbook.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "cell_range": cell_range,
            "rule_type": rule_type,
        }

    @locked_by_path
    def set_xlsx_data_validation(
        self,
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
        from openpyxl import load_workbook
        from openpyxl.worksheet.datavalidation import DataValidation

        if validation_type not in _DATA_VALIDATION_TYPES:
            raise ValueError(
                f"Unknown validation_type {validation_type!r}. Use one of: "
                f"{', '.join(sorted(_DATA_VALIDATION_TYPES))}"
            )
        file_path = self._check_editable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]

        # A plain comma list ("Yes,No,Maybe") needs to be Excel's own
        # quoted-literal form ('"Yes,No,Maybe"') to work as a dropdown --
        # a range reference (contains ":") or an already-quoted/formula
        # value is left alone, the same "don't make the model remember an
        # OOXML wrinkle" reasoning write_xlsx's own _xlfn. prefixing uses.
        if (
            validation_type == "list"
            and ":" not in formula1
            and not formula1.startswith(("\"", "="))
        ):
            formula1 = f'"{formula1}"'

        # `type`/`operator` are Literal-typed in openpyxl's stubs; both are
        # already checked against `_DATA_VALIDATION_TYPES`/a plain default
        # string at runtime above, mypy just can't narrow a `str` parameter
        # to a Literal on its own.
        validation = DataValidation(
            type=validation_type,  # type: ignore[arg-type]
            operator=operator  # type: ignore[arg-type]
            if validation_type not in ("list", "custom")
            else None,
            formula1=formula1,
            formula2=formula2 or None,
            allow_blank=allow_blank,
            showErrorMessage=bool(error_message),
            error=error_message or None,
            errorTitle=error_title or None,
        )
        validation.add(cell_range)
        sheet.add_data_validation(validation)
        workbook.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "cell_range": cell_range,
            "validation_type": validation_type,
        }

    @locked_by_path
    def freeze_xlsx_panes(self, path: str, sheet_name: str, cell: str = "") -> dict[str, object]:
        from openpyxl import load_workbook

        file_path = self._check_editable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]
        if cell and cell.upper() != "A1":
            try:
                sheet.freeze_panes = cell
            except (ValueError, AttributeError) as exc:
                raise ValueError(f"Invalid cell {cell!r}: {exc}") from None
        else:
            sheet.freeze_panes = None
        workbook.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "freeze_panes": sheet.freeze_panes,
        }

    @locked_by_path
    def set_xlsx_column_width(
        self, path: str, sheet_name: str, columns: str, width: float
    ) -> dict[str, object]:
        from openpyxl import load_workbook
        from openpyxl.utils import column_index_from_string, get_column_letter

        file_path = self._check_editable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]

        start_letter, _, end_letter = columns.upper().partition(":")
        end_letter = end_letter or start_letter
        try:
            start_idx = column_index_from_string(start_letter)
            end_idx = column_index_from_string(end_letter)
        except ValueError as exc:
            raise ValueError(f"Invalid columns {columns!r}: {exc}") from None
        if end_idx < start_idx:
            raise ValueError(f"Invalid columns {columns!r}: end is before start")

        letters = [get_column_letter(idx) for idx in range(start_idx, end_idx + 1)]
        for letter in letters:
            sheet.column_dimensions[letter].width = width
        workbook.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "columns": letters,
            "width": width,
        }

    @locked_by_path
    def edit_xlsx_cells(
        self, path: str, sheet_name: str, start_cell: str, content: str
    ) -> dict[str, object]:
        from openpyxl import load_workbook
        from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

        rows = _parse_table_rows(content)
        if not rows:
            raise ValueError("content has no rows to write")

        file_path = self._check_editable(path)
        workbook = load_workbook(str(file_path))
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Sheet {sheet_name!r} not found. Available sheets: {workbook.sheetnames}"
            )
        sheet = workbook[sheet_name]

        try:
            start_col_letter, start_row = coordinate_from_string(start_cell)
            start_col = column_index_from_string(start_col_letter)
        except ValueError as exc:
            raise ValueError(f"Invalid start_cell {start_cell!r}: {exc}") from None

        for row_offset, row in enumerate(rows):
            for col_offset, raw_cell in enumerate(row):
                sheet.cell(
                    row=start_row + row_offset, column=start_col + col_offset
                ).value = _coerce_cell(raw_cell)

        has_formula = _workbook_has_any_formula(workbook)
        workbook.save(str(file_path))

        recalc_result: dict[str, object] = {"status": "skipped", "skipped_reason": None}
        if has_formula:
            recalc_result = _recalc_xlsx_and_evaluate_lookups(file_path)

        preview_path, preview_skipped_reason = render_thumbnail(file_path, self._state_dir)
        return {
            "path": self._scope.relative(file_path),
            "sheet": sheet_name,
            "start_cell": start_cell,
            "rows_written": len(rows),
            "cols_written": max(len(row) for row in rows),
            "bytes_written": file_path.stat().st_size,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
            "recalc_status": recalc_result["status"],
            "recalc_skipped_reason": recalc_result.get("skipped_reason"),
            "total_formulas": recalc_result.get("total_formulas"),
            "total_errors": recalc_result.get("total_errors"),
            "formula_error_locations": recalc_result.get("error_locations"),
        }
