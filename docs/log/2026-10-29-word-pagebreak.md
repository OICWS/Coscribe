# `[PAGEBREAK]` in the writers' markdown, and a Word skill that does not polish by script (shipped)

Why: the maintainer's packaged app showed a docx turn with many steps: the agent wrote scripts to
fix numbering, size and indent and to put a template block "alone on one page", converted to PDF
and read each version, and asked a reviewer. The subset had no way to say "new page" (a cover page, a
block that stands alone), so a script was the only way.

## Shipped
- A line `[PAGEBREAK]` (also `[PAGE BREAK]`) starts the next block on a new page in `write_docx`,
  `edit_docx_structure` and `write_pdf`. In Word it is "page break before" on the next paragraph, so
  no empty line opens the new page; before a table or a contents list an empty paragraph starts it.
- The Word skill says so, and says what to do about layout the subset cannot say: write once, look at
  the preview once, fix with the tools, tell the person what could not be done; no PDF round trips
  and no script to polish the file.

## Not measured
- The maintainer's own prompt is not known here. Two runs of a similar brief (a guide with a template
  at the end, as a Word file) took 8 and 17 model calls with no script; the loop did not reproduce.
  Whether the new skill text removes it is unmeasured.
