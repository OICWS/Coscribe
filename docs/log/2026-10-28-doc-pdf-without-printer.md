# A Doc's PDF no longer goes through a printer in the desktop app (shipped)

Why: "Export as PDF" opened the system's print dialog, and its "Save as PDF" printer is not on every
machine; the maintainer asked for it to work without one.

## Shipped
- Desktop: `docPdf.ts` (main) prints the window with Chromium's own `printToPDF`, A4, 0.7 in margins,
  backgrounds on, and hands the bytes back; the preload exposes `printToPdf()`.
- Frontend: the page is copied into `#doc-print-root` and the window is made to hold only that copy for
  the moment (`body.doc-printing`, `@media print` in `index.css`), in the light theme whatever the app's,
  without the comments' marks and without a chart's source block under its drawing. A heading is kept
  with the paragraph after it, and a table, callout, chart, list item or picture is not split across a
  page. The bytes are saved as `<name>.pdf` as a Word export is.
- A browser tab keeps the print dialog.
- The repeated Doc callout/chart block in `index.css` is one copy now.

## Not verified
- The Electron call itself: no desktop shell here. The print rules were run through Chromium's own
  `page.pdf()` (the engine `printToPDF` uses) on a long Doc with a heading, tasks, a callout, a chart and
  a table, and the two pages read: light page, no app, chart source gone, nothing split.
