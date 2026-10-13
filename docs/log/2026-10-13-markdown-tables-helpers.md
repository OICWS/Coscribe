# The documents / _chart_data import cycle is gone (shipped)

Why: `tools/_chart_data.py` imported two table helpers from `tools/documents.py`, and `documents.py` reaches `_chart_data` through the chart tool, so docx, xlsx and charts could not be split into separate packages. Part of #105, closes #108.

## Shipped
- `_split_table_row`, `_is_separator_row` and the `_SEPARATOR_CELL_RE` they use moved unchanged from `tools/documents.py` to the new `tools/_markdown_tables.py`; `documents.py`, `_chart_data.py` and `spreadsheets.py` import them from there.
- `grimp` finds no import chain from `coscribe.tools._chart_data` to `coscribe.tools.documents` any more (on main it finds a direct one).
- `file_lines` for `documents.py` goes from 1938 to 1928 in `quality/baseline.json`.

## Not verified
- The Windows CI job was not run locally.

## Follow-ups
- `parse_blocks` and the other shared pieces move with the docx/xlsx split, not here.
