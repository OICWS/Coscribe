"""Writing a workbook from block and object operations: execute, guard, recalculate, check.

A new workbook is recalculated in place, so every viewer shows its numbers. A user's existing
workbook is saved by openpyxl alone, marked to recalculate when opened, and recalculated only on
a copy for the results and the checks: LibreOffice's resave would rewrite its styles and drop
features (decision 0011)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from .blocks import parse_blocks, parse_ops
from .column_layout import explicit_width_starts, widen_after_recalc, widen_for_values
from .engine_objects import apply_ops
from .engine_openpyxl import conflicts, write_block
from .findings import Written, check
from .guard import copy_path, inventory, load_watching, losses
from .helpers import _recalc_xlsx_and_evaluate_lookups

_RESULTS_LISTED = 40


def _open(path: Path) -> tuple[Any, list[str], Written]:
    from openpyxl import Workbook

    written = Written()
    if not path.exists():
        workbook = Workbook()
        for sheet in list(workbook.worksheets):
            workbook.remove(sheet)
        return workbook, [], written
    workbook, dropped = load_watching(path)
    written.sheets_with_content = {
        sheet.title
        for sheet in workbook.worksheets
        if any(cell.value is not None for row in sheet.iter_rows() for cell in row)
    }
    return workbook, dropped, written


def _save(workbook: Any, path: Path, existed: bool) -> Path:
    if existed:
        workbook.calculation.fullCalcOnLoad = True
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".~{path.stem}.coscribe{path.suffix}")
    workbook.save(str(temporary))
    return temporary


def _place(temporary: Path, path: Path, existed: bool, lost: list[str]) -> Path:
    target = copy_path(path) if existed and lost else path
    temporary.replace(target)
    return target


def _recalculated(target: Path, existed: bool, scratch: Path) -> tuple[Path, dict[str, Any]]:
    """The file whose cached values are the results: the target itself when it is new, else a
    recalculated copy in `scratch`."""
    if not existed:
        return target, _recalc_xlsx_and_evaluate_lookups(target)
    copy = scratch / f"recalc{target.suffix}"
    shutil.copyfile(target, copy)
    return copy, _recalc_xlsx_and_evaluate_lookups(copy)


def _formula_cells(workbook: Any, written: Written) -> dict[str, list[str]]:
    return {
        name: [c for c, _ in cells if str(workbook[name][c].value).startswith("=")]
        for name, cells in written.cells.items()
        if name in workbook.sheetnames
    }


def _widen(target: Path, values_path: Path, formulas: dict[str, list[str]], existed: bool) -> None:
    """Columns wide enough for the computed numbers, which only exist after recalculation. A new
    file keeps LibreOffice's values, so only its `<cols>` are patched."""
    if not existed:
        for name, cells in formulas.items():
            widen_after_recalc(target, name, cells)
        return
    from openpyxl import load_workbook

    workbook = load_workbook(str(target), keep_vba=target.suffix.lower() == ".xlsm")
    values = load_workbook(str(values_path), data_only=True)
    for name, cells in formulas.items():
        sheet = workbook[name]
        starts = explicit_width_starts(target, name)
        widen_for_values(sheet, values[name], [sheet[c] for c in cells], starts)
    workbook.calculation.fullCalcOnLoad = True
    workbook.save(str(target))


def _results(workbook: Any, values: Any, written: Written) -> dict[str, Any]:
    """The computed value of each formula written, so a wrong one shows in this call."""
    listed: dict[str, Any] = {}
    total = 0
    for name, cells in written.cells.items():
        for coordinate, _ in cells:
            if name in workbook.sheetnames and str(workbook[name][coordinate].value).startswith(
                "="
            ):
                total += 1
                if len(listed) < _RESULTS_LISTED:
                    listed[f"{name}!{coordinate}"] = values[name][coordinate].value
    return {"formula_results": listed, "formulas_not_listed": total - len(listed)}


def _finish(
    path: Path, workbook: Any, dropped: list[str], written: Written, deleted: bool
) -> dict[str, Any]:
    from openpyxl import load_workbook

    existed = path.exists()
    before = inventory(path) if existed else None
    temporary = _save(workbook, path, existed)
    try:
        lost = [] if before is None else losses(before, inventory(temporary), dropped, deleted)
        target = _place(temporary, path, existed, lost)
    finally:
        temporary.unlink(missing_ok=True)
    formulas = _formula_cells(workbook, written)
    with tempfile.TemporaryDirectory(prefix="coscribe_xlsx_") as scratch:
        values_path, recalc = _recalculated(target, existed, Path(scratch))
        if recalc.get("status") != "skipped":
            _widen(target, values_path, formulas, existed)
        saved = load_workbook(str(target))
        values = load_workbook(str(values_path), data_only=True)
        report = {
            "path": str(target),
            "saved_as_copy": target != path,
            "lost_if_saved_over_original": lost,
            "recalc": recalc,
            **_results(saved, values, written),
            "findings": check(saved, values, target, written),
        }
    return report


def _fit(workbook: Any, path: Path, written: Written) -> None:
    """Widen only the columns just written to, so a user's own layout stays as it was."""
    for name, cells in written.cells.items():
        sheet = workbook[name]
        starts = explicit_width_starts(path, name) if path.exists() else set()
        widen_for_values(sheet, None, [sheet[c] for c, _ in cells], starts)


def write_cells(
    path: Path, blocks: Any, styles: Any = None, overwrite: bool = False
) -> dict[str, Any]:
    """`write_xlsx_cells`: blocks of cells with their styles, then recalculated and checked."""
    parsed = parse_blocks(blocks, styles)
    workbook, dropped, written = _open(path)
    clashing = [] if overwrite else conflicts(workbook, parsed)
    if clashing:
        raise ValueError(
            f"{len(clashing)} cells already hold something else, e.g. {clashing[:5]}; "
            "read them, then write again with overwrite=true if they should be replaced"
        )
    for block in parsed:
        for cell, looked in write_block(workbook, block):
            written.add(block.sheet, cell.coordinate, looked)
    _fit(workbook, path, written)
    return _finish(path, workbook, dropped, written, deleted=False)


def modify_workbook(path: Path, ops: Any) -> dict[str, Any]:
    """`modify_xlsx`: sheets, rows and columns, charts, rules, print setup and names."""
    parsed = parse_ops(ops)
    if not path.exists() and not any(op["op"] == "add_sheet" for op in parsed):
        raise ValueError(f"{path.name} does not exist; write cells to it first")
    workbook, dropped, written = _open(path)
    apply_ops(workbook, parsed)
    for op in parsed:
        if op.get("sheet") in workbook.sheetnames:
            written.cells.setdefault(op["sheet"], [])
    deleted = any(op["op"] == "delete_sheet" for op in parsed)
    return _finish(path, workbook, dropped, written, deleted)
