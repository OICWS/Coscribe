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

## Not verified
- Excel on Windows opening the cached charts. LibreOffice opens and draws them (checked by hand).
- The effect on 097, 098, 082 and 091, measured in a rerun the maintainer approves.

## Follow-ups
- None.
