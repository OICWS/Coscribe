# The Word export keeps a callout's look, draws a chart natively and writes task boxes (shipped)

Why: the maintainer exported Docs to Word and saw a callout reduced to a bold word, a chart left as
its table, and `[ ]` text in a bullet. Word's own look was a stated goal of the export (decision 0025).

## Shipped
- A callout is framed in its colour (the editor's: note blue, tip green, important purple, warning
  amber, caution red) with a tinted background and its label above, as the editor draws it.
- A chart is a native Word chart built from its table (bar, line, pie); a table that is no data stays
  as a table under the chart's title.
- A task item `- [ ]` / `- [x]` is `☐` / `☑` in front of the text, without a bullet.
- The export hands the writer marker paragraphs; `docx/_markers.py` does the rest on the finished file,
  because the markdown subset cannot say any of this. `write_docx` is unchanged.

## Not verified
- How Word itself draws them; checked in LibreOffice's rendering of the file only (callout frame,
  chart, boxes all as intended).

Found by reading seven real Docs the agent wrote, exported: a callout's label alone at the bottom of a
page (a callout now stays with its label across a page break), and a Doc's `---` printed as dashes (it
is a hairline now).
