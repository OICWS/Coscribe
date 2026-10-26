# The Word editor and Review view draw a document as it looks

Date: 2026-10-26
Area: frontend, tools

The Docs editor showed a Word file in the app's own style (grey lines for tables, contents and
charts), far from what Word shows. It now draws the file the way it is laid out:

- The server resolves each paragraph's look through its styles and direct formatting (`docx/look.py`:
  font, size, colour, spacing, indents, rules, fill; theme colours and fonts included) and sends it
  as `look`; a run's colour, size and font that differ from its paragraph's ride on the run
  (`c`, `sz`, `f`) and are written back when the person edits that paragraph. The paragraph's own
  properties are never rewritten.
- Tables carry widths, borders, cell fills and padding (`docx/block_tables.py`). A table the editor
  cannot change (merged or nested cells) is sent whole and drawn read-only, rowspans included.
- The document sits on a sheet of its page size and margins, scaled to fit the panel.
- A chart is drawn from its chart part as an SVG (`lib/docxChart.ts`: bar, column, line, area, pie), in the
  editor and in Review (docx-preview leaves an empty box there). `jszip` is now a direct dependency.
- Review no longer applies a file's `stylesWithEffects` part, which docx-preview laid over the real
  styles (blue template headings on a green document).

Not verified: a real Windows machine and Word's own fonts (checked in Chromium against a LibreOffice
render of the same file). Contents entries are drawn without Word's right-aligned tab and dot leader,
and headers, footers and page breaks are not shown in the editor.
