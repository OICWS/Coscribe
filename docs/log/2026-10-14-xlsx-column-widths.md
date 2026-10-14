# write_xlsx sizes the columns of the sheet it writes (shipped)

Why: workbooks the agent made with `write_xlsx` kept the default column width (8.43 characters), so
LibreOffice cut labels (`Unit price`, `Open tickets`, `销售额（万元）`) and printed numbers that did
not fit as `###` (#193, found by the Excel evaluation of #164).

## Shipped
- `tools/office/xlsx/column_widths.py`: a cell is measured as Excel shows it: a number with its
  number format applied (`#,##0"元"`, `0.0%`, `$#,##0;($#,##0)`, a General number at most 11
  characters), a CJK or full-width character as two. A column is widened to its longest value
  plus 2 characters when that exceeds the default, and never past 50. Formula cells have no value
  before LibreOffice recalculates, so their column is sized by the header and constants. Text with
  an empty cell to its right (a title over a table) does not widen its column, except in the
  sheet's last column.
- `write_xlsx` calls it on the sheet it wrote. A width set on that sheet before (by
  `set_xlsx_column_width` or in the user's template) is carried over when the sheet is replaced and
  is not resized; before this a replaced sheet lost those widths. Nothing is reported to the model.
- The xlsx goldens change only by the new `<cols>` elements (12 sheets in 7 goldens); the
  `column_widths` golden, whose widths are set explicitly, is unchanged.
- `tests/test_xlsx_column_widths.py`: a label is no longer clipped (the evaluation's own
  `clipped_texts` check), a formatted number gets room, number formats, CJK, the cap, a title over
  empty cells, a kept width, a template width.

## Not verified
- The model run of the affected Excel tasks (`03-lookup-two-sheets`, `07-chinese-formats`,
  check `legibility`) was not made: the work finished in DeepSeek's peak hours.
- A number format applied after `write_xlsx` (by `format_xlsx_cells`) does not resize the column;
  a header usually leaves enough room (`销售额（元）` is 12 wide, `12,850,000元` too), but not always.
- Excel on Windows was not opened; widths were checked against LibreOffice's rendering rules only.

## Follow-ups
- Whether `format_xlsx_cells` should widen a column whose new format no longer fits (the same
  measure applies).
