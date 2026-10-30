"""Cell parsing and formula checks behind the xlsx tools."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet

# SORT/FILTER/UNIQUE/SEQUENCE stay blocked -- they're "dynamic array"
# functions (spill a result across multiple cells), which needs real
# Excel-365-only OOXML machinery openpyxl can't write (a `t="array"`
# `<f>`/`cm=` cell plus a new `xl/metadata.xml` part; reference:
# `jmcnamara/XlsxWriter`, BSD-2-Clause), and IronCalc returns #SPILL! for
# them. Writing a partial version (values with no spill metadata) would
# silently populate only the top-left cell rather than failing loudly, so
# still hard-blocked rather than half-supported. XLOOKUP/XMATCH in their
# scalar form need no spill metadata, and IronCalc evaluates them.
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


def _validate_and_normalize_formula(formula: str) -> str:
    """`formula` is a cell string starting with `=`. Raises ValueError for
    a dynamic-array function (see _XLSX_UNSUPPORTED_FUNCTIONS' comment);
    auto-prefixes the functions Excel itself stores with a hidden `_xlfn.`
    prefix so the model doesn't
    have to know that OOXML wrinkle."""
    for name in _XLSX_UNSUPPORTED_FUNCTIONS:
        if re.search(rf"\b{name}\s*\(", formula, re.IGNORECASE):
            raise ValueError(
                f"Formula {formula!r} uses {name}(), which spills over several cells and "
                f"has no spill-range metadata when openpyxl writes it -- only the "
                f"top-left cell would silently get a value. Use INDEX/MATCH for lookups; "
                f"sort, filter, and de-duplicate data in Python before writing the cells."
            )
    for name in _XLSX_XLFN_FUNCTIONS:

        def _prefix(match: re.Match[str], name: str = name) -> str:
            return f"_xlfn.{name}{match.group(1)}"

        formula = re.sub(rf"(?<!_xlfn\.)\b{name}(\s*\()", _prefix, formula, flags=re.IGNORECASE)
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
