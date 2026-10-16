# Excel part 1c: the ten old writers removed, two harder tasks (shipped)

Why: decision 0011's part 1c, after part 1b met its gate. The agent had two ways to write a
workbook, the ten single-purpose tools and the block tools; one is clearer and cheaper.

## Shipped
- The agent's Excel tools are now `read_xlsx`, `recalc_xlsx`, `write_xlsx_cells` and
  `modify_xlsx`. Removed:
  - `write_xlsx`, `edit_xlsx_cells`;
  - `format_xlsx_cells`;
  - `merge_xlsx_cells`, `unmerge_xlsx_cells`;
  - `add_xlsx_chart`, `add_xlsx_conditional_format`, `set_xlsx_data_validation`;
  - `freeze_xlsx_panes`, `set_xlsx_column_width`.

  The tool list goes from 122 to 112 tools.
- The two block tools are `SpreadsheetToolkit` methods now, so the approval card's
  before/after preview covers them, as it covered the old writers. `block_tools.py` became
  `csv_blocks.py` (the `from_csv` reader); the helpers only the old tools used are gone.
- Two evaluation tasks:
  - **11-rich-workbook**: adding to a user's plan that has a sparkline, which openpyxl cannot
    keep. The new check `original_keeps` fails when the user's file lost it, so the result
    must be a new file.
  - **12-big-ledger**: 5,000 orders from a CSV, with amounts and region totals as formulas.
    An input probe sets the Desk price to 0 on a copy and the North total must move.

  Both reference solutions (openpyxl, and the block operations, where the guard writes
  `plan_2026 (coscribe).xlsx`) pass every check.
- Tests: the old tools' tests are gone or ported to the new tools (read, recalc, scoping,
  concurrency, column widths, approval preview). The xlsx goldens pinned the old writers' XML
  and are removed with them. The frontend keeps the old tools' labels for old conversations.

## Not verified
- The model on tasks 01-12 with only the four tools: the off-peak run is next, and the gate is
  the same as part 1b's.
- In Excel on Windows: task 11's copy and the 5,000-row workbook.

## Follow-ups
- 1d, the preview panel.
