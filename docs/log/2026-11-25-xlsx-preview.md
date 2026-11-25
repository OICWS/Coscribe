# Read-only Excel workbook preview (shipped)

Why: users need to inspect workbook layout, formulas and figures inside a conversation (#1073).

## Shipped

- Generated workbook links, attachments and Files use the same read-only grid with worksheet tabs,
  cell selection, a formula bar, scrolling, merged cells and frozen panes.
- The server reads the selected sheet and its stored formula results locally. Common cell styles,
  embedded raster images and basic bar, column and line charts render in the sheet.

## Not verified

- The Windows Electron shell and an original opened at the same time in Microsoft Excel.
- Advanced conditional formatting and specialized drawings are outside the preview. Some custom
  formats can look different in Excel.
