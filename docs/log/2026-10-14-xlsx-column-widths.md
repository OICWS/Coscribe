# write_xlsx sizes the columns of the sheet it writes (shipped)

Why: workbooks the agent made with `write_xlsx` kept the default column width (8.43 characters), so
LibreOffice cut labels (`Unit price`, `Open tickets`, `销售额（万元）`) and printed numbers that did
not fit as `###` (#193, found by the Excel evaluation of #164).

## Shipped
- `tools/office/xlsx/column_widths.py` measures a cell as Excel shows it: a number with its number
  format applied (`#,##0"元"`, `0.0%`, `$#,##0;($#,##0)`, `0.00E+00`, `#,##0,"K"`, quoted and
  escaped `;`), a General number at most 11 characters, a CJK or full-width character as two
  (the same rule as the evaluation's `legibility` check). Fractions, dates and `@` are measured
  by the longer of the format's own length and the General text.
- `tools/office/xlsx/column_layout.py`: a column is widened to its longest value plus 2 when that
  exceeds the default, never past 50. Text over empty cells to its right widens its column only
  when it is longer than that run of cells (up to the sheet's last column). A formula cell has
  no value yet, so its column is sized by its header and constants (and, after LibreOffice
  recalculates, by its values: `2026-10-14-xlsx-widths-after-recalc.md`).
- The columns `write_xlsx` sized are listed per sheet in a custom document property,
  `coscribe.fitted_columns` (LibreOffice drops `bestFit`, but keeps custom properties). When a
  sheet is written again, those columns are sized again for the new content; any other width
  (a template's, or one `set_xlsx_column_width` set, which takes the column off the list) is
  kept. The rest of a replaced sheet's columns (hidden, outline level, style, ranges such as
  `A:XFD`) is carried over as ranges; before this, replacing a sheet dropped all of it. A `<col>`
  without a width (only hidden or styled) does not count as a set width. Nothing is reported to
  the model.
- The xlsx goldens change by the added `<cols>` elements and by the new `docProps/custom.xml`
  part (with its content type and relationship).
- `tests/test_xlsx_column_widths.py` (19 tests).

## Not verified
- The model run of the affected Excel tasks (`03-lookup-two-sheets`, `07-chinese-formats`, check
  `legibility`) was not made: the work finished in DeepSeek's peak hours.
- A width a person changes in Excel by hand on a column `write_xlsx` sized is not told apart from
  the sized one, so writing the sheet again sizes it again.
- Excel on Windows was not opened; widths were checked against LibreOffice's rendering only.

## Follow-ups
- `format_xlsx_cells` and `edit_xlsx_cells` do not resize: a number format applied after
  `write_xlsx` that no longer fits the column can still print `###`; the same measure applies.
