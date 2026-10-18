# A workbook with a cell note gets its formula values again (shipped)

Why: batch 10 item 1 (#425). A workbook with a note made the formula engine skip the whole file
("Zip Error: specified file not found in archive"), so its formulas got no cached value.

## Shipped
- Cause: openpyxl writes a sheet's comments part with an absolute target
  (`/xl/comments/comment1.xml`); IronCalc joins it onto the sheet's folder and cannot find it.
  Relative targets load fine (checked on the same file). `calc.py` now hands the engine a copy with
  the sheet's absolute targets made relative; the values are written into the real file, which is
  not otherwise changed. A file that is not a zip is reported as unreadable, as before.
- `formula_results` listed a `text: true` cell whose text starts with `=` (for example `=001`).
  Whether a cell is a formula now comes from its cell type, not its text.
- Tests, each failing without the fix: a note plus a formula gets its value
  (`test_a_workbook_with_a_note_still_gets_its_formula_values`), a text cell is not listed as a
  formula, and the note golden now has a total (`=SUM(C2:C3)` computes 15.5 beside the note).

## Not verified
- Notes written by Excel itself (relative targets) were not tried; the change leaves them as
  they were.

## Follow-ups
- Other places still decide "is a formula" by `startswith("=")` (`findings.py`, `overview.py`); whether a
  `text: true` cell is mistaken for a formula there was not checked.
