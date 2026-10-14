# write_xlsx and format_xlsx_cells widen columns to what they show (shipped)

Why: workbooks the agent made with `write_xlsx` kept the default column width (8.43 characters), so
LibreOffice cut labels (`Unit price`, `Open tickets`, `销售额（万元）`) and printed numbers that did
not fit as `###` (#193, found by the Excel evaluation of #164).

## Shipped
- `tools/office/xlsx/column_widths.py` measures a cell as Excel shows it: a number with its number
  format applied (`#,##0"元"`, `0.0%`, `$#,##0;($#,##0)`, `0.00E+00`, `#,##0,"K"`, quoted and
  escaped `;`), a General number at most 11 characters, a CJK or full-width character as two
  (the same rule as the evaluation's `legibility` check). Fractions, dates and `@` are measured
  by the longer of the format's own length and the General text.
- `tools/office/xlsx/column_layout.py`: a column gets its longest shown value plus 2, never more
  than 50, and only when that is wider than what it has. Columns are only ever widened:
  - `write_xlsx` sizes the sheet it wrote. Text over empty cells to its right widens its column
    only when it is longer than that run of cells (up to the sheet's last column). A formula has
    no value yet, so its column is sized by its header and constants.
  - When `write_xlsx` replaces a sheet, each column of the old sheet is carried over whole
    (width, hidden, outline level, style, and ranges such as `A:XFD`); before this, replacing a
    sheet dropped all of it. A width set earlier (by `set_xlsx_column_width`, a template or an
    earlier write) is kept unless the new content needs more; a width that is now too wide is
    not shrunk. A hidden column and a column of width 0 are left exactly as they were (openpyxl
    would drop `width="0"` on save, so it is written explicitly). A `<col>` without a width does
    not count as a set width.
  - `format_xlsx_cells` with a `number_format` widens the columns of the range to show their
    values under the new format (formula cells by the value LibreOffice last computed). This is
    the `###` of the Chinese-format task: `12850000` becomes `12,850,000元` after `write_xlsx`.
- Nothing is reported to the model. The xlsx goldens change only by the added `<cols>` elements.
- `tests/test_xlsx_column_widths.py` (20 tests).

## Not verified
- The model run of the affected Excel tasks (`03-lookup-two-sheets`, `07-chinese-formats`, check
  `legibility`).
- Excel on Windows was not opened; widths were checked against LibreOffice's rendering only.
- `format_xlsx_cells` sees a formula's value only while the file still holds what LibreOffice
  computed: its own save drops those values (as before), so a second format call on another
  formula column of the same workbook measures its header and constants only. Seen live: after
  formatting B and then C (`=B2/10000` as `#,##0.00"万"` under a short header), C printed `###`.

## Follow-ups
- Next PR (`tools/xlsx-widths-after-recalc`): size a column of formulas from the values
  LibreOffice computed, after the recalculation `write_xlsx` already runs.
- `edit_xlsx_cells` does not resize columns.
