# A chart of workbook data lands in the workbook, and can be redone there (shipped)

Why: asked to "draw" a quadrant chart of a workbook's data (OfficeVal dev task 098), the agent went
straight from `read_xlsx` to a plotting script. It handed back a picture in a Word document or a
deck in six runs of six. The coordinator's prompt already says a workbook's chart is native, but
the agent never loaded the Excel skill and never looked at `modify_xlsx`.

## Shipped
- `read_xlsx`'s result ends with one paragraph: a chart of this data goes into this workbook as a
  native chart through `modify_xlsx`, which the Excel skill explains. With it, all four runs
  loaded the skill and charted in the workbook.
- A `chart` op at a cell where a chart already stands replaces it. A new `delete_chart` op removes
  one chart, or every chart on a sheet. One run had cleared its chart with an openpyxl script so
  it could redo it, ended with none, and scored 0.
- The edit guard counts the charts and drawings an edit removed on purpose. Without that, the
  deletion went to a "(coscribe)" copy as if the file had lost them.
- Excel skill: how to redo a chart.
- 098 (dev): 0 in six runs before (a picture, not a chart). After: 0.82 and 0 with the note alone,
  then 0.87 and 0.87 with the replace and delete ops ($0.05 a run).

## Not verified
- The chart in the real Excel on Windows; checked in LibreOffice only.

## Follow-ups
- Neither of the two 0.87 runs used item names as point labels or kept the sheet free of extra
  notes; both are choices the agent makes.
