# write_xlsx widens a column of formulas to the computed values (shipped)

Why: `write_xlsx` widens the columns of the sheet it writes to what they show
(`2026-10-14-xlsx-column-widths.md`), but a formula has no value until LibreOffice recalculates
the saved file, so a column of formulas under a short header (`Total`, `占比`) kept its width and
a large result could still print as `###` (#193).

## Shipped
- After the recalculation `write_xlsx` and `edit_xlsx_cells` already run when a workbook has
  formulas, `column_layout.widen_after_recalc` reads the computed values of the formula cells
  the call wrote and widens their columns by the same rule as the rest: the shown value plus 2,
  never past 50, never narrower than the column already is, a hidden or zero-width column left
  alone.
- The widths are patched into `<cols>` of the saved sheet: saving through openpyxl again would
  drop every computed value. A `<col>` range the column falls in is split; the rest of the range
  keeps its width and look. The preview is rendered after the patch.
- Tests: the patch widens and splits a range but never narrows; a column holding only
  `=123456789012/7` under the header `Sum` gets at least 11 characters, from `write_xlsx` and
  from `edit_xlsx_cells` (real LibreOffice). This is `Orders!D6` `Desk lamp` of the lookup task
  (03): an `INDEX`/`MATCH` result written with `edit_xlsx_cells`.

## Not verified
- Excel on Windows was not opened; checked against LibreOffice only.
- A sheet whose XML uses a prefixed namespace (`x:cols`) is left unpatched. The patched file is
  always the one LibreOffice just saved, which uses the default namespace.
