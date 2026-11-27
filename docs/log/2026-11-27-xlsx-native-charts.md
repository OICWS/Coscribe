# A workbook's charts are native and carry their values (shipped)

Why: on the OfficeVal dev tasks (#1078), two Excel tasks lost almost all their points on charts.
In 098 the agent drew the chart as a picture with a script and inserted it, so the checker found
no chart. In 097 it wrote 16 charts with openpyxl in a script, on a helper sheet, with no values
in the chart part. A person gets the same faults: a picture they cannot edit, and an empty chart
in a file preview.

## Shipped
- Every save of a workbook (`write_xlsx_cells` or `modify_xlsx`) writes each chart's values and
  labels into the chart, the cache Excel writes, so a chart follows a later change to its cells.
  A series of formulas gets none, since its values wait for recalculation. Text categories are
  written as text.
- The Excel skill and the coordinator prompt:
  - a workbook's chart is native, from `modify_xlsx`;
  - its source is the table the person sees;
  - a reference line is a two-point series;
  - many charts go in one call.

## Measured
On the OfficeVal dev tasks with charts, one run each, deepseek-flash:
- 097: 0.03 to 0.69. The 16 charts are native, made with `modify_xlsx`.
- 098: still 0 in two runs. Asked only to "draw" a chart, the agent made a PNG (and once a Word
  file) and never opened the Excel tools.

091 (0.87) and 082 are not chart tasks.

## Not verified
- Excel on Windows opening the cached charts. LibreOffice opens and draws them (checked by hand).

## Follow-ups
- 098: the agent does not take a chart of workbook data as a workbook job when the request
  doesn't say where the chart goes (`docs/plan.md`).
