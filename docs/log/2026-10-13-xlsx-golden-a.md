# xlsx goldens: plain, multi-sheet formulas, widths, panes, merges (partly shipped)

Why: `tools/spreadsheets.py` (1,439 lines) is on the ratchet's file-size list and is to be split by pure moves. As for the pptx tools, the XML of the workbooks it writes is pinned first, so a later split can be shown to change nothing (issue #107, part of #105).

## Shipped
- `office-agent/tests/test_xlsx_golden.py` builds five workbooks through the public tools and compares their canonical text (`tests/pptx_canonical.py`, unchanged) with `tests/golden/xlsx/<name>.txt`: `plain`, `multi_sheet_with_formulas` (three sheets, numbers, text, dates as text, SUM, a growth ratio, an INDEX/MATCH lookup across sheets), `column_widths`, `frozen_panes` and `merged_and_unmerged`.
- `tests/golden/xlsx/_shared.txt` keeps the theme, package relationships and `docProps/app.xml` once. `UPDATE_GOLDENS=1` rewrites all of them.
- The test module's docstring says `recalc_xlsx` is not covered. The LibreOffice pass after a formula write and the thumbnail are switched off, so formulas have no cached value.
- Stability probe: two processes with different `PYTHONHASHSEED` and different directories gave identical bytes in every part except `docProps/core.xml`, whose `dcterms:created` and `dcterms:modified` are the build time; those two are the only blanked values.

## Not verified
- On Windows: the nightly Windows job runs these tests. Nothing in them depends on a path separator.

## Follow-ups
- Part b: number formats, fonts and fills, conditional formats, data validation, a chart and `edit_xlsx_cells`.
