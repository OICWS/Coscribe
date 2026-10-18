# Tables can be typed into, and have a properties panel

Why: a table on a slide could be moved and resized but its cells could not be edited, and its
columns, rows and header could not be changed.

## Shipped
- Typing into a table's cells in place (`useTableEditing.ts`): a double-click or Enter draws the
  table in the editor with typeable cells (`sectionDom.ts`, in place of the server's picture of
  it, which returns after the save); Tab and Shift+Tab move between cells, Enter is a line break,
  Escape or a press away ends it and writes the cells' text back into the section's table.
- `SlideTableProperties.tsx`: Columns, Rows (a new row or column copies the last, blank; the first
  row of a header-only table adds body rows), Header row (the first row's `th` and `td`), each
  column's width (written as a `colgroup`, all columns at once; "Share the width evenly" removes
  it), and the table's font, size, text colour, background and border colour.
- `lib/slideTable.ts`: those changes to a section's `<table>`.

## Checked
- In Chromium against a live server: a table inserted, two cells typed into with Tab and Shift+Tab,
  columns and rows changed to 4, a column's width set, the header row turned off; each step
  matched in the saved section.

## Not verified
- Not opened in PowerPoint. `slideTable.ts` and `slideText.ts` have no unit tests that touch the
  DOM: the unit tests run without one (#425 item 10 adds one).
- Cell-level settings (one cell's fill, alignment, role), merged cells, adding or deleting one row
  or column in the middle, and the mockup's Resize and Effects are not offered.

## Follow-ups
- Select a cell and give it its own properties; add and delete a row or column at the cell.
