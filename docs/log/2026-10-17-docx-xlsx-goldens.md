# Golden tests for xlsx, and more for docx (shipped)

Why: plan step 9 had pptx goldens only (issue #402, item 7). A change to what the Word and
Excel tools write, a style, a cell value, a chart, showed up nowhere until a person opened
the file.

## Shipped
- `tests/test_xlsx_golden.py`: 11 workbooks built through `write_xlsx_cells` and `modify_xlsx`
  (styled table, dates/notes/text cells, `like_row`, `fill_down_to`, CSV, CJK, layout and print
  setup, sheets, column and line charts, conditional formats and validation), compared with
  `tests/golden/xlsx/*.txt`.
- `tests/xlsx_canonical.py`: a `<cells>` section (each cell's value, formula with its cached
  result, number format, font, fill, alignment, border, note) followed by every XML part,
  pretty-printed with sorted attributes and no build times; the stock theme is a hash.
- `tests/test_docx_golden.py`: 3 more documents (`edit_docx_structure` plain and tracked,
  a comment with a reply through `edit_docx_review`); `tests/docx_canonical.py` numbers the
  random `w15:paraId` of a comment thread in order of appearance, keeping the reply link.
- Regenerate: `UPDATE_GOLDENS=1 pytest tests/test_xlsx_golden.py tests/test_docx_golden.py`.
- Proved by breaking the code: ignoring `bold`, dropping the number format, leaving ISO
  dates as text and dropping italic runs each fail the goldens with a readable diff.

## Not verified
- Windows (CI runs it); the goldens were generated on Linux.

## Follow-ups
- Product bug, filed on #402: a workbook with a cell note makes the formula engine skip
  recalculation ("Zip Error"), so formulas get no cached value. The note workbook avoids
  formulas until it is fixed.
