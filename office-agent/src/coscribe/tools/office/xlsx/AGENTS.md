# tools.office.xlsx: Excel (.xlsx) read, write and modify tools

## Purpose
Owns the spreadsheet tools: reading each sheet with its layout, writing engine-neutral blocks
of cells (`blocks.py`, `csv_blocks.py`) through openpyxl (`engine_openpyxl.py`,
`engine_objects.py`), column widths and layout, the guard that stops a user's workbook losing
content (`guard.py`), the findings checks (`findings.py`) and formula recalculation with IronCalc
(`calc.py`). Does not own Word, PDF or PowerPoint, or how the viewer draws a workbook.

## Public interface
`SpreadsheetToolkit`, `build_spreadsheet_tools`. Import them from `coscribe.tools.office.xlsx`.

## Depends on
`coscribe.runtime`, `coscribe.tools._file_locks`, `coscribe.tools._output_truncation`,
`coscribe.tools._workspace`.

## Invariants
- A workbook is written as engine-neutral blocks, not engine calls
  (`docs/decisions/0011-workbooks-are-written-as-engine-neutral-blocks.md`).
- Formula values are computed in-process and written into the file; no spreadsheet application
  is required (`docs/decisions/0012-the-product-does-not-depend-on-libreoffice.md`).
- `guard.py` runs before every save of an existing workbook.

## Tests
`tests/test_spreadsheets_tool.py`, `tests/test_xlsx_blocks.py`, `tests/test_xlsx_calc.py`,
`tests/test_xlsx_column_widths.py`, `tests/test_evals_xlsx.py`.

## Verify by hand
A written workbook with formulas, charts and conditional formats opened in the real Excel on
Windows.

## Reviewed
2026-10-17 (first card).
