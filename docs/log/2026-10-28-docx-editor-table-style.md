# A Word table keeps its borders and header row in the editor (shipped)

Why: a document coscribe wrote with a table opened in Word with a blue header row and borders, and in
the editor as a bare grid-less table with a pale header (the maintainer's side-by-side screenshot).

## Shipped
- The house table style keeps its borders (`tblBorders`) and the first row's fill and white bold text
  (`tblStylePr firstRow`) in the style, not in each cell. The editor's reader (`look.py`,
  `block_tables.py`) took only the table's and the cells' own formatting. It now reads the table's
  style chain: the borders, and, where the table's `tblLook` turns them on (as the attribute, or the
  hexadecimal `val` of older files), the first and last row's fill, border, text colour and bold.
  A cell's own formatting still wins. Tables the editor cannot change (`locked_grid`) get the same.
- `test_a_table_carries_what_its_style_gives_it_borders_and_a_header_row`; without the change it
  fails.

## Checked
- In the real editor, run with the stub model, on a Word file written by `write_docx`: the grid, the
  blue header with white bold text and the bold total row show.

## Not verified
- A table made by Word itself, with its own table styles (banded rows and first column are not read:
  only the first and last row and the borders).
- The packaged app.

## Follow-ups
- Banded rows and the first column, if a document needs them.
