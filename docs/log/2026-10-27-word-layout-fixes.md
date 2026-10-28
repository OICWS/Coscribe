# Word reports: table headers, the contents title and column charts (shipped)

Why: the maintainer found the Word output low in quality and the contents list messy. Four
reports (evaluation tasks 01, 09, 12, 14) were written by the real agent and their pages read.

## Shipped
- A table's header row is set bold, but its column widths were measured plain, so "Measure",
  "Shipments" and "Complaints" broke in the middle of a word. `_table_layout` takes `header=True`
  and measures the first row bold (`table_layout.py`, `_xml.py`).
- A heading reading "Contents" (or "Table of contents", "目录") above `[TOC]` is now the list's
  title ("TOC Heading", outside the list). Only the insert operation retitled it; `write_docx` and
  the Docs export never did, so the list opened with its own title. Any other heading above the
  list is left as it is, since it can be the document's title.
- A column chart's axis starts at 0 when no value is negative (it started at 39,000 for values of
  41,200 to 44,600), and the chart's text takes the document's typeface instead of a serif fallback.
- A plain paragraph right after a table has 6 pt above it.
- The Word skill said Word recalculates the contents list on open; it no longer does (the
  update-fields prompt is gone), so the skill says the list has no page numbers, that neither
  page numbers nor page breaks go in by script, that a cover and a contents list suit about six
  pages or more, and that headline figures do not belong in large type in a many-column table.
- Goldens `chart`, `cjk`, `table` and `structure_edit_tracked` changed: column widths a few
  twips, the chart's axis and fonts.

## Measured
Tasks 01, 12 and 14 rerun once each (DeepSeek flash, low effort, off-peak): every fact is still
there (13/13, 16/16, 12/12) and the pages show whole header words, no self-listing in the
contents, a zero-based axis and a sans chart font. Cost 0.012 / 0.023 / 0.022 USD; one run each,
so the cost difference from the first run is not a result.

## Not verified
- The files opened in Word on Windows; the pages were drawn by LibreOffice 24.2.
- That the skill's new sentences change what the model writes: the rerun did not build a
  statistics card at all, so that one was not exercised.
- The note under a table (an italic paragraph) still sits against the table in task 12; it is
  not the plain paragraph kind and was not looked into.

## Follow-ups
- Page numbers in the contents list, from Word itself when it is installed (COM). Without Word
  there is no honest way to number pages.
- The Docs artifact's cards and the Word panel were not looked at in this pass.
