# "Make something new" no longer offers Sheets (shipped)

Why: the maintainer decided that a workbook is best made and opened in Excel, that a table to look at
in the app is a Dashboard (HTML, CSS and JavaScript), and that a tile named like Docs and Slides
promised an in-app grid the app does not have.

## Shipped
- `TILE_ORDER` in `lib/artifacts.ts` is the page's kinds without `sheets`; `NewTiles` draws it.
  Workbooks the conversations made are still listed, under Sheets in the filter, and open in Excel.
- A unit test pins the tiles: Docs, Slides, Design, Dashboard (still "Soon", kept as the direction),
  Design system.

## Not verified
- The page in a browser (the change is the list the tiles are drawn from).

## Follow-ups
- Whether `.docx` files should stay listed as files, without the in-app editor: asked, not decided.
