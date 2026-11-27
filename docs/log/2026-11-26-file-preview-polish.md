# Steadier sheet scrolling and calmer file previews (shipped)

Why: in the Excel preview the row numbers and frozen panes trailed the sheet while the scrollbar
was dragged; Markdown in Files showed its raw text before the rendered page; the Word preview
spent a row on page buttons that scrolling already covers; worksheet tabs had almost no hover state.

## Shipped
- Row numbers, column letters and frozen panes are sticky layers the browser moves with the scroll.
  With the CPU slowed 4x and fast wheel scrolling, 26 of 112 frames had the row numbers 120 px
  (and the column letters 400 px) out of place before; 0 of 105 after. The grid draws 12 rows and
  4 columns past each edge.
- Markdown in Files appears once, rendered; the renderer loads beside the text (time to the
  rendered heading in the dev server: 1.1 s before, 0.35 s after, no raw-text frame).
- The Word preview has no toolbar row: a small control in the corner shows the page, the zoom and
  Open in Word.
- Worksheet tabs: no Read-only note; hover, press, focus and selected states.

## Not verified
- The Windows Electron app (checked in Chromium on Linux).
