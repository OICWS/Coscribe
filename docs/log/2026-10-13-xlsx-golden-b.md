# xlsx goldens: formats, conditional formats, validation, charts, cell edits (shipped)

Why: second half of issue #107. Part a pinned the structure tools (widths, panes, merges, formulas); this part pins the styling and the objects the workbook tools add, so a later split of `tools/spreadsheets.py` can be shown to change nothing.

## Shipped
- Seven more workbooks in `office-agent/tests/test_xlsx_golden.py`, 12 in all: `number_formats_and_fonts` (currency, percent, negative-in-parentheses codes, font colour, bold), `conditional_formats` (cell-is with `<` and `between`, a three-colour scale, a data bar), `data_validation` (a list, a whole-number range, a decimal minimum, a list from a range on another sheet), `chart_bar`, `chart_line_three_series` (with an anchor), `chart_pie_subset` (with a data range), and `edit_cells_keeps_structure` (`edit_xlsx_cells` on a workbook with merges, number formats and frozen panes, including a formula).
- Same stability result as part a: only `docProps/core.xml` creation and modification times vary between runs.
- Charts: only the three types `add_xlsx_chart` offers (bar, line, pie) exist, and all three are pinned.
- `format_xlsx_cells` has no fill argument, so fills are covered through the conditional formats' fill colours.

## Not verified
- On Windows: the nightly Windows job runs these tests.

## Follow-ups
- None for #107.
