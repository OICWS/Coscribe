"""Excel (.xlsx) tools, scoped to a single workspace root (decision 0011).

`read_xlsx` shows each sheet as a table with its layout (styles, formats, formulas, rules,
charts). `write_xlsx_cells` writes blocks of cells with their formulas and styles, a whole table
or workbook per call; `modify_xlsx` changes sheets, layout and objects. A block or an operation
is engine-neutral data (`blocks.py`), executed by openpyxl (`engine_openpyxl.py`,
`engine_objects.py`), then guarded against losses in a user's workbook (`guard.py`) and
checked (`findings.py`).

Formula values are computed by `calc.recalculate` with IronCalc, in-process, and written into
the file (decision 0012), so a viewer that does not calculate still sees them; `recalc_xlsx`
does it for a workbook written some other way.
"""

from __future__ import annotations

from .toolkit import SpreadsheetToolkit
from .tools import build_spreadsheet_tools

__all__ = ["SpreadsheetToolkit", "build_spreadsheet_tools"]
