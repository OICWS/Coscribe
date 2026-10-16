# Workbook formula values computed with IronCalc, not LibreOffice (shipped)

Why: the xlsx tools computed formula values, and checked them for errors, by running a
LibreOffice found on the user's machine. Windows does not ship it and coscribe's users do not
install it, so on their machines formulas came back without values or checks. Decision
[0012](../decisions/0012-the-product-does-not-depend-on-libreoffice.md).

## Shipped
- `tools/office/xlsx/calc.py`: IronCalc (`ironcalc` 0.9.0, MIT/Apache-2.0, a 3.3 MB wheel)
  evaluates the saved workbook in-process and each formula cell gets its value written into
  the file; `fullCalcOnLoad` stays set, so Excel recalculates on open. The report keeps the
  shape the tools returned (`status`, `total_formulas`, `total_errors`, `error_locations`).
- `write_xlsx`, `edit_xlsx_cells`, `recalc_xlsx`, `write_xlsx_cells` and `modify_xlsx` use it.
  An edit to a user's workbook now returns computed values too; the note saying it had none is
  gone. `recalc_xlsx` lost its `timeout` argument.
- The XLOOKUP/XMATCH evaluator (`tools/_xlsx_lookup_formulas.py`, 2 test files) is removed:
  IronCalc computes both, nested in other formulas too. The mutation job tests `calc.py`
  instead.
- A formula IronCalc cannot compute (`#NAME?` from a function or name Excel has, e.g.
  CUBEVALUE, and the cells that depend on it) is listed as `unchecked` with no value, never as
  the model's error; an unknown function or an undefined name stays a `#NAME?` error.
- Measured: the same value as LibreOffice for all 89 formula cells of the ten Excel evaluation
  tasks. FILTER and UNIQUE give `#SPILL!`; the tools already refuse them.
- The golden workbooks now pin the computed values. The packaged server collects `ironcalc`.

## Not verified
- The packaged Windows build with the `ironcalc` native module.
- A real user's workbook full of functions IronCalc lacks: only the `#NAME?` case is
  separated; a function IronCalc has but computes differently from Excel would go unnoticed.

## Follow-ups
- Decision 0012 steps 2 and 3 (#319): previews and conversion through Office, then removing
  the LibreOffice code paths.
