# spreadsheets.py is now tools/office/xlsx (shipped)

Why: decision 0010 puts each office format in its own package under `tools/office/`; this is the second half of the move started with `documents.py`. Part of #147, closes it.

## Shipped
- A pure move, split by line range; bodies and docstrings are unchanged.
- `tools/office/xlsx/helpers.py`: cell parsing, formula checks and the LibreOffice recalculation (`_recalc_xlsx`, `_recalc_xlsx_and_evaluate_lookups`).
- `tools/office/xlsx/toolkit.py`: `SpreadsheetToolkit`.
- `tools/office/xlsx/tools.py`: `build_spreadsheet_tools`, same tool order and docstrings.
- `tools/__init__.py` now also exports `SpreadsheetToolkit`, so `session.py` imports it from the package. `_xlsx_lookup_formulas.py` and `_native_formula/` stay where they were.

## Checked
- `tests/tool_schemas.txt`, `tests/web_routes.txt` and the xlsx goldens are byte-identical; tests changed only in import lines (two alias the moved module as `spreadsheets`, so the monkeypatches in `conftest.py` and the golden test still patch the module that holds `_recalc_xlsx` and `find_soffice`).
- `lint-imports`, mypy and ruff pass. In `quality/baseline.json` `spreadsheets.py` is gone, `build_spreadsheet_tools` (419 lines) is listed under its new path, and `deep_imports` shrinks by two.

## Not verified
- The Windows CI job was not run locally.
