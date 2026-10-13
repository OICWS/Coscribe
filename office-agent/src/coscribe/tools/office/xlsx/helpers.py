"""Cell parsing, formula checks and the LibreOffice recalculation behind the xlsx tools."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..._office_bins import find_soffice, run_soffice
from ...office.markdown_blocks import _is_separator_row, _split_table_row

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

_XLSX_RECALC_TIMEOUT = 30.0

# SORT/FILTER/UNIQUE/SEQUENCE stay blocked -- they're "dynamic array"
# functions (spill a result across multiple cells), which needs real
# Excel-365-only OOXML machinery openpyxl can't write and this package
# hasn't built yet (a `t="array"` `<f>`/`cm=` cell plus a new
# `xl/metadata.xml` part -- see `_xlsx_lookup_formulas.py`'s own module
# docstring for the real, verified reference: `jmcnamara/XlsxWriter`,
# BSD-2-Clause). Writing a partial version (values with no spill metadata)
# would silently populate only the top-left cell rather than failing
# loudly, so still hard-blocked rather than half-supported.
#
# XLOOKUP/XMATCH are NOT blocked -- their common *scalar* usage (one
# lookup value, one result) needs no spill metadata at all, and
# `_xlsx_lookup_formulas.py` evaluates them natively (LibreOffice itself
# can't -- confirmed empirically it lowercases the function name and
# writes a real #NAME? error rather than crashing).
_XLSX_UNSUPPORTED_FUNCTIONS = ("SORT", "FILTER", "UNIQUE", "SEQUENCE")

# Excel stores these post-2007 functions with a hidden `_xlfn.` prefix in
# the file's XML (its UI hides the prefix) -- written bare, each evaluates
# to #NAME? in real Excel. First six confirmed against Anthropic's own
# published xlsx skill; XLOOKUP/XMATCH confirmed against `formulas`
# (vinci1it2000, real open-source formula-evaluation library)'s own
# `FUNCTIONS['_XLFN.XLOOKUP']`/`FUNCTIONS['_XLFN.XMATCH']` registrations --
# plain `_xlfn.`, not the `_xlfn._xlws.` prefix FILTER/SORT need (those
# stay hard-blocked above, unrelated to this list).
_XLSX_XLFN_FUNCTIONS = (
    "TEXTJOIN",
    "CONCAT",
    "IFS",
    "SWITCH",
    "MAXIFS",
    "MINIFS",
    "XLOOKUP",
    "XMATCH",
)

_XLSX_ERROR_STRINGS = ("#VALUE!", "#DIV/0!", "#REF!", "#NAME?", "#NULL!", "#NUM!", "#N/A")

# ThisComponent.calculateAll() + store() + close() via a StarBasic macro is
# the only way that actually forces LibreOffice to recalculate every
# formula and write back cached values -- plain `soffice --convert-to`
# reuses whatever's already cached (nothing, for an openpyxl-written file).
# Same technique Anthropic's own xlsx skill's recalc.py uses. Verified
# empirically in this sandbox (see _recalc_xlsx's docstring): invoking the
# macro requires priming a throwaway LibreOffice profile first (an
# uninitialized one has no basic/Standard library for the macro to load
# into), then overwriting that profile's default Module1.xba.
_XLSX_RECALC_MACRO = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">
<script:module xmlns:script="http://openoffice.org/2000/script"
    script:name="Module1" script:language="StarBasic">
    Sub RecalculateAndSave()
      ThisComponent.calculateAll()
      ThisComponent.store()
      ThisComponent.close(True)
    End Sub
</script:module>"""


def _parse_table_rows(content: str) -> list[list[str]]:
    """Parse pipe-table-only markdown (no headings/bullets/paragraphs --
    a spreadsheet is a grid, not flowing text) into raw string rows."""
    rows: list[list[str]] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cells = _split_table_row(line)
        if cells is None:
            raise ValueError(
                f"write_xlsx content must be pipe-table rows only (`| cell | cell |`), "
                f"got: {line!r}"
            )
        if _is_separator_row(cells):
            continue
        rows.append(cells)
    return rows


def _validate_and_normalize_formula(formula: str) -> str:
    """`formula` is a cell string starting with `=`. Raises ValueError for
    a function LibreOffice can never evaluate (see
    _XLSX_UNSUPPORTED_FUNCTIONS' comment); auto-prefixes the six functions
    Excel itself stores with a hidden `_xlfn.` prefix so the model doesn't
    have to know that OOXML wrinkle."""
    for name in _XLSX_UNSUPPORTED_FUNCTIONS:
        if re.search(rf"\b{name}\s*\(", formula, re.IGNORECASE):
            raise ValueError(
                f"Formula {formula!r} uses {name}(), which LibreOffice (used to verify "
                f"every formula this tool writes) cannot evaluate under any prefix, and "
                f"which has no spill-range metadata when openpyxl writes it -- only the "
                f"top-left cell would silently get a value. Use INDEX/MATCH for lookups; "
                f"sort, filter, and de-duplicate data in Python before writing the cells."
            )
    for name in _XLSX_XLFN_FUNCTIONS:

        def _prefix(match: re.Match[str], name: str = name) -> str:
            return f"_xlfn.{name}{match.group(1)}"

        formula = re.sub(
            rf"(?<!_xlfn\.)\b{name}(\s*\()", _prefix, formula, flags=re.IGNORECASE
        )
    return formula


# Excel keeps 15 significant digits; a longer number is an identifier.
_EXCEL_DIGITS = 15
_PLAIN_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")


def _coerce_cell(value: str) -> Any:
    if value.startswith("="):
        return _validate_and_normalize_formula(value)
    text = value.strip()
    # Only what a person would type as a plain number. Python's int()/float()
    # also take "00123" (an ID, becomes 123), "1_000", "1e5", "inf"/"NaN"
    # (became empty cells) and full-width digits, and a 19-digit card number
    # became a rounded float -- silent data loss.
    if _PLAIN_NUMBER.fullmatch(text) and len(text.lstrip("-").replace(".", "")) <= _EXCEL_DIGITS:
        return float(text) if "." in text else int(text)
    return value


def _render_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _render_sheet_table(sheet: Worksheet) -> str:
    lines = []
    for row in sheet.iter_rows():
        lines.append("| " + " | ".join(_render_cell(cell.value) for cell in row) + " |")
    return "\n".join(lines)


def _recalc_xlsx(file_path: Path, timeout: float = _XLSX_RECALC_TIMEOUT) -> dict[str, object]:
    """Force LibreOffice to recalculate every formula in `file_path` and
    rewrite it in place. Never raises -- any failure (soffice missing,
    timeout, a workbook with external file links that recalculating would
    destroy) comes back as `status: "skipped"` with a reason, the same
    graceful-degradation contract as write_pptx's overflow QA. Verified
    empirically in this sandbox: a bare `soffice --convert-to` does NOT
    recalculate (it just re-emits whatever's already cached -- nothing,
    for a file openpyxl just wrote); only the macro-based
    calculateAll()+store()+close() approach actually does.
    """
    soffice = find_soffice()
    if soffice is None:
        return {"status": "skipped", "skipped_reason": "LibreOffice (soffice) not found"}

    try:
        with zipfile.ZipFile(file_path) as archive:
            has_external_links = any(
                name.startswith("xl/externalLinks/") for name in archive.namelist()
            )
    except (zipfile.BadZipFile, OSError) as exc:
        return {"status": "skipped", "skipped_reason": f"could not inspect workbook: {exc}"}
    if has_external_links:
        return {
            "status": "skipped",
            "skipped_reason": (
                "workbook links to another file -- recalculating would resolve those "
                "links' cells to #NAME? and delete the links for good, since openpyxl "
                "already stripped their cached values on save"
            ),
        }

    profile_dir = Path(tempfile.mkdtemp(prefix="coscribe_xlsx_recalc_"))
    try:
        profile_url = profile_dir.as_uri()
        try:
            run_soffice(
                [
                    soffice,
                    "--headless",
                    "--terminate_after_init",
                    f"-env:UserInstallation={profile_url}",
                ],
                timeout,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as exc:
            return {
                "status": "skipped",
                "skipped_reason": f"could not prepare a LibreOffice profile: {exc}",
            }

        macro_dir = profile_dir / "user" / "basic" / "Standard"
        if not macro_dir.is_dir():
            return {
                "status": "skipped",
                "skipped_reason": "LibreOffice did not create a usable profile",
            }
        (macro_dir / "Module1.xba").write_text(_XLSX_RECALC_MACRO, encoding="utf-8")

        # A run that times out is killed, so it works on a copy: the
        # workbook is never left half-saved.
        work_copy = profile_dir / f"recalc{file_path.suffix}"
        shutil.copyfile(file_path, work_copy)
        try:
            run_soffice(
                [
                    soffice,
                    "--headless",
                    "--norestore",
                    f"-env:UserInstallation={profile_url}",
                    "vnd.sun.star.script:Standard.Module1.RecalculateAndSave"
                    "?language=Basic&location=application",
                    str(work_copy),
                ],
                timeout,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as exc:
            return {
                "status": "skipped",
                "skipped_reason": f"LibreOffice failed to recalculate: {exc}",
            }
        shutil.copyfile(work_copy, file_path)
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

    return _scan_xlsx_formulas(file_path)


def _scan_xlsx_formulas(file_path: Path) -> dict[str, object]:
    """Count every formula cell and every real Excel error string
    (`#DIV/0!` etc.) currently in `file_path`. Factored out of `_recalc_xlsx`
    so `_recalc_xlsx_and_evaluate_lookups` can call it a second time, after
    its own native XLOOKUP/XMATCH pass, to get the true final count -- the
    first scan (right after LibreOffice's own recalc) is stale for any cell
    that pass goes on to patch."""
    from openpyxl import load_workbook

    values_workbook = load_workbook(str(file_path), data_only=True)
    error_locations: dict[str, list[str]] = {}
    total_errors = 0
    for sheet_name in values_workbook.sheetnames:
        sheet = values_workbook[sheet_name]
        if not hasattr(sheet, "iter_rows"):
            continue
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    for error_string in _XLSX_ERROR_STRINGS:
                        if error_string in cell.value:
                            error_locations.setdefault(error_string, []).append(
                                f"{sheet_name}!{cell.coordinate}"
                            )
                            total_errors += 1
                            break
    values_workbook.close()

    formulas_workbook = load_workbook(str(file_path), data_only=False)
    formula_count = 0
    for sheet_name in formulas_workbook.sheetnames:
        sheet = formulas_workbook[sheet_name]
        if not hasattr(sheet, "iter_rows"):
            continue
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formula_count += 1
    formulas_workbook.close()

    return {
        "status": "success" if total_errors == 0 else "errors_found",
        "total_formulas": formula_count,
        "total_errors": total_errors,
        "error_locations": {
            error: locations[:20] for error, locations in error_locations.items()
        },
    }


def _recalc_xlsx_and_evaluate_lookups(
    file_path: Path, timeout: float = _XLSX_RECALC_TIMEOUT
) -> dict[str, object]:
    """`_recalc_xlsx`'s LibreOffice pass, followed by
    `_xlsx_lookup_formulas.evaluate_and_patch_lookup_formulas` for the two
    functions LibreOffice can't compute at all (confirmed empirically --
    see that module's own docstring: LibreOffice lowercases the function
    name and writes a real `#NAME?` error rather than crashing or leaving
    other formulas unrecalculated). The single entry point `write_xlsx`/
    `edit_xlsx_cells`/`recalc_xlsx` call instead of `_recalc_xlsx` directly,
    so a workbook's XLOOKUP/XMATCH cells get real values through the exact
    same "recalc after every formula write" path as everything else.
    """
    result = _recalc_xlsx(file_path, timeout=timeout)
    if result["status"] == "skipped":
        return result  # LibreOffice itself unavailable -- nothing to layer on top of

    from ..._xlsx_lookup_formulas import evaluate_and_patch_lookup_formulas

    native_result = evaluate_and_patch_lookup_formulas(file_path)
    if not native_result["formulas_evaluated"]:
        return result

    # Re-scan rather than patch the counts by hand -- the native pass can
    # both fix a #NAME? LibreOffice left *and* legitimately introduce a
    # new #N/A/#VALUE! of its own (a genuinely-not-found lookup, mismatched
    # range lengths), so LibreOffice's own pre-native-pass report is stale
    # either way, not just "off by the count we already know."
    return _scan_xlsx_formulas(file_path)


def _workbook_has_any_formula(workbook: Any) -> bool:
    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        if not hasattr(sheet, "iter_rows"):
            continue
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    return True
    return False


_CHART_TYPES = frozenset({"bar", "line", "pie"})

_CONDITIONAL_FORMAT_RULE_TYPES = frozenset({"cell_is", "color_scale", "data_bar"})

_DATA_VALIDATION_TYPES = frozenset(
    {"list", "whole", "decimal", "date", "time", "textLength", "custom"}
)
