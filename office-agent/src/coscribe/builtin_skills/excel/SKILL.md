---
name: Excel Spreadsheets
description: How to build or change an Excel workbook with write_xlsx_cells and modify_xlsx - layout, formulas, styles, charts, and checking the result. Load before writing a workbook.
---
## Plan the workbook, then write it whole

Decide first, in two or three lines, what the reader needs: which sheets, what each holds,
where the inputs are and where the results go.
- A report for a manager starts with a summary sheet (the key figures, a breakdown, a chart)
  and keeps the raw data on its own sheet behind it.
- A model puts every assumption in one labelled block, one per cell with its unit, and the
  calculation below or beside it, one period per column.

Then write it with `write_xlsx_cells`, the whole table or the whole workbook in one call:
- one block per table;
- the header styled through `row_styles`;
- number formats through `col_styles`;
- the styles named once in `styles`.

Add charts, freeze panes, column widths, conditional formats and print setup with **one**
`modify_xlsx` call. Two or three calls make a good workbook; twenty small ones make a worse
one.

For a large input (hundreds of rows), give the block `"from_csv": "明细.csv"` instead of
`rows`: the tool copies the file and you never retype it. If the data is messy, clean it into
a CSV with `run_python_script` (pandas) first. The totals stay formulas in the workbook.

## Formulas over typed numbers, always

Every result is a formula on the cells it comes from, never a number you computed:
- `=SUMIF(明细!B:B,A2,明细!F:F)`, `=B5*(1+$B$3)`;
- an assumption is referenced by its cell (`$B$3`), never retyped into a formula;
- use the same formula shape along a row or column; `fill_down_to` repeats it.

A typed number between formulas is the most common silent error, and the result reports it.
Use SUMIF/SUMIFS/COUNTIF/INDEX/MATCH. Avoid FILTER, UNIQUE, SORT and SEQUENCE, which the tool
refuses.

## Make it readable

- **Header row**: bold, with a fill (white text on a dark fill reads well), and frozen with
  `{"op": "freeze", "at": "A2"}`.
- **Number formats** on every number:
  - thousands separators: `#,##0`;
  - the unit in the header (`销售额（元）`, `Revenue ($)`) rather than in each cell;
  - percentages stored as fractions, shown as `0.0%`;
  - dates as `yyyy-mm-dd`.
- **Financial models**: inputs in blue font (`0000FF`), formulas in black, links to another
  sheet in green (`008000`).
- **Charts**: a chart where a trend or a comparison is the point, with a title, anchored
  beside its table (two columns right of it), never over cells that hold data.
  - A chart in a workbook is always a native one, from `modify_xlsx`'s `chart` op, so the
    person can edit it and it follows the data. It is never a picture drawn in a script and
    inserted, and never a chart a script writes with openpyxl.
  - Its source is the table the person sees, such as each question's own rows for a chart per
    question. Use a helper sheet only when the data must be reshaped first.
  - A chart of the person's workbook goes into that workbook, beside their table, charting
    their cells as they are. Never copy the data into a new workbook to chart it there, and
    never split, rename or retype their columns for the chart.
  - A reference line (a mean, a target) across a line or column chart is one more series of
    two points.
  - A quadrant chart (importance against satisfaction, impact against effort) is a scatter
    whose axes cross at the two means (`x_cross`, `y_cross`): the x column with `x`, the y
    column as `source`, each point named from its label column with `point_labels`, the axis
    ends set close around the data, and no legend or gridlines.
  - Fonts and sizes the request names for the chart's text go in `font`, such as
    `{"size": 9, "latin": "Times New Roman", "east_asian": "宋体"}`.
  - Many charts go in the same single `modify_xlsx` call.
- **Columns** widen themselves to what they show; set a width only for a long label column.
- **Print setup**: a report or a sheet with a chart is printed or sent as a PDF, so give it
  `{"op": "print", "sheet": ..., "landscape": true, "fit_width": 1}`, which keeps every column
  and the chart on the page.

## Changing a user's workbook

- **Read it first** (`read_xlsx`): its `Layout:` lines name the header's look, each
  column's number format and formula, frozen panes, rules and charts. No script is needed to
  inspect it.
- **Match its look**:
  - a new column takes the look of its neighbour with `"like": "C2"`;
  - a new row takes each column's look with `"like_row": 7`.

  Keep their conventions over these defaults.
- **Cells that hold something** are not written over unless `overwrite` is true. Read them
  and be sure before you set it.
- **If the result says `saved_as_copy`**, the user's file has something that could not be kept
  (`lost_if_saved_over_original`). Tell the user where the new file is and what it lacks.

## Check before saying it is done

Each call returns:
- `formula_results`, the value every formula you wrote computed. Compare two or three with
  what you expect by hand;
- `recalc`, formula errors by cell;
- `findings` by cell: `###`, cut-off text, a typed number between formulas, a chart over data,
  a new cell unlike the table above it.

Fix what they name in one more call. After two rounds, stop and say what is left. If a number
has no clear source, say where it came from.
