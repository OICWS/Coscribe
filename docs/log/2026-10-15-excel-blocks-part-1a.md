# Excel part 1a: block and object operations, a guard and a checker (shipped, not offered yet)

Why: decision 0011. A workbook written whole scored 4.1 of 5 on design, against 2.8–3.2 for the
many-small-tools route. Claude for Excel and Microsoft's Agent Mode write a block of cells with
its styles per call and return the computed results. This is that interface, engine-neutral,
with openpyxl as its first engine. No tool exposes it yet: part 1b registers it and measures it.

## Shipped
In `tools/office/xlsx/`:
- **`blocks.py`**: the operations, parsed and validated before anything is written.
  - A block: a sheet, a top-left cell, and rows of values, formulas or cell objects.
  - Styles are named once or given per block, row, column or cell.
  - `like` copies one cell's look and `like_row` each column's look from a row.
  - `fill_down_to` repeats the last row with its formulas moved.
  - An ISO date becomes a real date.
  - The object operations: sheets, columns and rows, freeze, merge, charts by source range
    and anchor, conditional formats, validation lists, print setup and names.
- **`engine_openpyxl.py` and `engine_objects.py`**: execute them. Nothing is overwritten
  unless asked, and the refusal names what is there.
- **`guard.py`**: what an openpyxl save would drop from a user's workbook, from openpyxl's
  own warnings and a count of the file's parts. The write then goes to `<name>
  (coscribe).xlsx` and names the losses; the original is left as it was.
- **`build.py`**:
  - a new workbook is recalculated in place;
  - a user's workbook is saved by openpyxl with `fullCalcOnLoad` and recalculated on a copy;
  - only the columns written to are widened;
  - each write returns the computed value of every formula it wrote.
- **`findings.py`**, findings by cell:
  - `###`;
  - text cut off by a filled neighbour;
  - a typed number between formulas;
  - a chart over filled cells;
  - a new cell unlike the filled cell above it (headers excepted).

## Checked
- The reference solutions of all ten Excel tasks, rebuilt through the operations only
  (`tests/xlsx_reference_blocks.py`), pass every evaluation check with LibreOffice.
- On those builds the checker reported nothing after the header fix (two findings on a first
  data row under its header, before it).
- A workbook with sparklines edited through a block goes to a copy, and the copy's report names
  the lost sparklines.

## Not verified
- In Excel on Windows: a file saved with `fullCalcOnLoad` and no cached values (how
  Explorer's and Outlook's preview panes show it), and the charts' look.
- Pivot tables, slicers and form controls in the guard: they cannot be made here without Excel.

## Follow-ups
- Part 1b: the two tools (`write_xlsx_cells`, `modify_xlsx`), `read_xlsx`'s overview, the
  skill and the coordinator text, measured on tasks 01–10.
- Inserting and deleting rows and columns is left out: openpyxl does not move formulas,
  merges or charts with them. It needs its own design or the Excel engine.
