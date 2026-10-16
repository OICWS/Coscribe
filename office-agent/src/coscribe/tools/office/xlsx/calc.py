"""Formula values without Excel or LibreOffice (decision 0012): IronCalc evaluates the saved
workbook in-process, and each formula cell gets its computed value written into the file.

openpyxl writes a formula with no cached value, so a viewer that does not calculate (a file
preview, a phone, a script reading values) saw blanks; the values written here fill that, and
the file keeps `fullCalcOnLoad`, so Excel still recalculates on open."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

_ERRORS_LISTED = 20
_CELL = r"\$?[A-Z]{1,3}\$?\d+"
_REFERENCE = re.compile(
    rf"^(?:.+!)?(?:{_CELL}(?::{_CELL})?|\$?[A-Z]{{1,3}}:\$?[A-Z]{{1,3}}|\$?\d+:\$?\d+)$",
    re.IGNORECASE,
)
_UNCHECKED = "uses a function the built-in formula engine does not have; Excel computes it"
_NAMESPACE = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
_RELATIONSHIP = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"


class _Error(str):
    """An error value (`#DIV/0!`), written with `t="e"`."""


def sheet_parts(entries: dict[str, bytes]) -> dict[str, str]:
    """`{sheet name: "xl/worksheets/sheetN.xml"}` through the workbook's relationships: the
    part names need not follow the sheet order."""
    from lxml import etree

    workbook = etree.fromstring(entries["xl/workbook.xml"])
    rels = etree.fromstring(entries["xl/_rels/workbook.xml.rels"])
    targets = {rel.get("Id"): rel.get("Target") for rel in rels.iter(_RELATIONSHIP)}
    parts: dict[str, str] = {}
    for sheet in workbook.iter(f"{_NAMESPACE}sheet"):
        name, target = sheet.get("name"), targets.get(sheet.get(_R))
        if name and target:
            # A target is absolute from the package root or relative to xl/; files use both.
            parts[name] = target[1:] if target.startswith("/") else f"xl/{target}"
    return parts


def _cached(value: Any) -> tuple[str, str | None]:
    """A value as `<v>` text and its `t=`, as Excel stores a formula's result: `e` an error,
    `b` a boolean, a number untyped, `str` a string (never `s`, the shared-string index)."""
    if isinstance(value, _Error):
        return str(value), "e"
    if isinstance(value, bool):
        return ("1" if value else "0"), "b"
    if isinstance(value, int | float):
        return (str(int(value)) if float(value).is_integer() else repr(float(value))), None
    return str(value), "str"


def _patch(cell: Any, value: Any) -> None:
    """Sets the cell's cached `<v>` right after its `<f>`, the order the schema requires."""
    from lxml import etree

    formula = cell.find(f"{_NAMESPACE}f")
    text, kind = _cached(value)
    if kind:
        cell.set("t", kind)
    elif "t" in cell.attrib:
        del cell.attrib["t"]
    stored = cell.find(f"{_NAMESPACE}v")
    if stored is None:
        stored = etree.Element(f"{_NAMESPACE}v")
        formula.addnext(stored)
    stored.text = text


def _formula_cells(path: Path) -> tuple[dict[str, list[tuple[int, int, str, str]]], set[str]]:
    """Each sheet's formula cells as (row, column, address, formula), and the workbook's defined
    names in lower case, read from the file's XML so a large workbook is not loaded into
    openpyxl a second time."""
    from lxml import etree

    with zipfile.ZipFile(path) as archive:
        entries = {
            name: archive.read(name)
            for name in archive.namelist()
            if name in ("xl/workbook.xml", "xl/_rels/workbook.xml.rels")
            or name.startswith("xl/worksheets/")
        }
    workbook = etree.fromstring(entries["xl/workbook.xml"])
    names = {(n.get("name") or "").lower() for n in workbook.iter(f"{_NAMESPACE}definedName")}
    found: dict[str, list[tuple[int, int, str, str]]] = {}
    for sheet, part in sheet_parts(entries).items():
        if part not in entries:
            continue
        for cell in etree.fromstring(entries[part]).iter(f"{_NAMESPACE}c"):
            formula = cell.find(f"{_NAMESPACE}f")
            if formula is not None:
                address = cell.get("r", "")
                row, col = _split(address)
                found.setdefault(sheet, []).append((row, col, address, formula.text or ""))
    return found, names


def _names_excel_knows(formula: str, defined: set[str]) -> bool:
    """Whether every function and name in `formula` is one Excel has: a `#NAME?` from such a
    formula is the engine's gap, not the formula's mistake. A function added to Excel after
    2010 is stored with the `_xlfn.` prefix, so the prefix is enough to know it."""
    from openpyxl.formula import Tokenizer
    from openpyxl.utils.formulas import FORMULAE

    if not formula:
        return False
    try:
        tokens = Tokenizer("=" + formula).items
    except ValueError:
        return False
    for token in tokens:
        if token.type == "FUNC" and token.subtype == "OPEN":
            name = token.value[:-1].upper()
            if not (name in FORMULAE or name.startswith(("_XLFN.", "_XLWS."))):
                return False
        elif token.type == "OPERAND" and token.subtype == "RANGE":
            value = token.value
            if "[" in value or _REFERENCE.match(value):
                continue
            if value.rsplit("!", 1)[-1].lower() not in defined:
                return False
    return True


def _split(address: str) -> tuple[int, int]:
    from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

    letters, row = coordinate_from_string(address)
    return row, column_index_from_string(letters)


def evaluate(path: Path) -> tuple[dict[str, dict[str, Any]], list[str], str | None]:
    """`{sheet: {address: value}}` for every formula cell the engine could compute, the cells it
    could not (`Sheet!A1`), or no values and why."""
    import ironcalc

    try:
        model = ironcalc.load_from_xlsx(str(path), "en", "UTC")
        model.evaluate()
        cells, defined = _formula_cells(path)
    except (ironcalc.WorkbookError, OSError, ValueError, RuntimeError, KeyError) as exc:
        return {}, [], f"the formula engine could not read this workbook: {exc}"
    sheets = [s["name"] for s in model.get_worksheets_properties()]
    values: dict[str, dict[str, Any]] = {}
    unchecked: list[str] = []
    for sheet, formulas in cells.items():
        if sheet not in sheets:
            continue
        index = sheets.index(sheet)
        for row, col, address, formula in formulas:
            value = model.get_cell_value(index, row, col)
            if model.get_cell_type(index, row, col) == ironcalc.CellType.ErrorValue:
                if value == "#NAME?" and _names_excel_knows(formula, defined):
                    unchecked.append(f"{sheet}!{address}")
                    continue
                value = _Error(value)
            values.setdefault(sheet, {})[address] = value
    return values, unchecked, None


def _write_values(path: Path, values: dict[str, dict[str, Any]]) -> None:
    from lxml import etree

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        entries = {info.filename: archive.read(info.filename) for info in infos}
    parts = sheet_parts(entries)
    for sheet, cells in values.items():
        part = parts.get(sheet)
        if part is None or part not in entries:
            continue
        root = etree.fromstring(entries[part])
        for cell in root.iter(f"{_NAMESPACE}c"):
            if cell.get("r") in cells and cell.find(f"{_NAMESPACE}f") is not None:
                _patch(cell, cells[cell.get("r", "")])
        entries[part] = etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", standalone=True
        )
    patched = path.with_name(path.name + ".values")
    with zipfile.ZipFile(patched, "w", zipfile.ZIP_DEFLATED) as archive:
        for info in infos:
            archive.writestr(info, entries[info.filename])
    patched.replace(path)


def recalculate(path: Path) -> dict[str, Any]:
    """Compute every formula of `path` and write the values into it. The report has the shape
    the xlsx tools always returned: `status`, `total_formulas`, `total_errors`,
    `error_locations` by error code, and `unchecked` for the cells the engine could not
    compute, which keep no value."""
    values, unchecked, problem = evaluate(path)
    if problem is not None:
        return {"status": "skipped", "skipped_reason": problem}
    _write_values(path, values)
    errors: dict[str, list[str]] = {}
    for sheet, cells in values.items():
        for address, value in cells.items():
            if isinstance(value, _Error):
                errors.setdefault(str(value), []).append(f"{sheet}!{address}")
    total_errors = sum(len(where) for where in errors.values())
    return {
        "status": "success" if total_errors == 0 else "errors_found",
        "total_formulas": sum(len(cells) for cells in values.values()),
        "total_errors": total_errors,
        "error_locations": {code: where[:_ERRORS_LISTED] for code, where in errors.items()},
        **(
            {"unchecked": {"cells": unchecked[:_ERRORS_LISTED], "why": _UNCHECKED}}
            if unchecked
            else {}
        ),
    }
