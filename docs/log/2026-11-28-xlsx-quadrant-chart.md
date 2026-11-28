# A native quadrant chart in Excel, and charts on workbooks without calculation settings (shipped)

Why: OfficeVal task 098 asks for an importance-satisfaction quadrant chart. `modify_xlsx` could
not make one (no point names, no axes crossing at the means, no chart fonts), and failed outright
on a workbook saved without calculation settings, such as that task's input.

## Shipped
- `modify_xlsx`'s `chart` op: a scatter's x values from another column (`x`), each point named
  from a label column (`point_labels`), axis ends and crossing points (`x_min`, `x_max`,
  `y_min`, `y_max`, `x_cross`, `y_cross`), the chart's font (`font`), and `legend` and
  `gridlines` off. A scatter now shows points, not a line joining them.
- `tools/office/xlsx/chart_labels.py`: a data label that keeps its own text, so the point names
  survive a later save of the workbook.
- `tools/office/xlsx/build.py`: a workbook without calculation properties gets them before it
  is saved, instead of the change failing.
- Excel skill: how to make a quadrant chart, set its fonts, and chart the person's own table.
- 098's input charted with one `modify_xlsx` call scores 45 of 45 with the benchmark's verifier.

## Not verified
- How Excel itself shows the chart (checked in LibreOffice only). A real Windows check is open.
- The agent did not pick Excel for 098 in four runs: it drew a picture into a Word document or
  a deck. Getting it to choose the workbook is a separate change.

## Follow-ups
- 098: the agent's choice of deliverable when a workbook's data is asked to be "drawn".
