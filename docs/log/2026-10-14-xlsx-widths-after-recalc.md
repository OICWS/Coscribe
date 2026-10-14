# write_xlsx sizes a column of formulas from the computed values (shipped)

Why: `write_xlsx` sizes the columns of the sheet it writes from what they show
(`2026-10-14-xlsx-column-widths.md`), but a formula has no value until LibreOffice recalculates
the saved file, so a column of formulas under a short header (`Total`, `占比`) kept the default
width and a large result could still print as `###` (#193).

## Shipped
- After the recalculation `write_xlsx` already runs when a sheet has formulas,
  `column_layout.widen_after_recalc` reads the computed values and widens each formula column
  of the written sheet that needs more room, never past 50 and never one with a kept width.
- The widths are patched into `<cols>` of the saved sheet: saving through openpyxl again would
  drop every cached value. A `<col>` range the column falls in is split, the rest of the range
  keeps its width and look. The preview is rendered after the patch.
- Tests: the patch splits a range and keeps the rest; a column holding only
  `=123456789012/7` under the header `Sum` gets at least 11 characters (real LibreOffice).

## Not verified
- Excel on Windows was not opened; checked against LibreOffice only.
- A sheet whose XML uses a prefixed namespace (`x:cols`) is left unpatched. The patched file is
  always the one LibreOffice just saved, which uses the default namespace.
