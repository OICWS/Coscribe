# 0013: Word documents gain a document style, not a script route

Status: proposed (2026-10-16). Evidence: `docs/assessments/2026-10-16-word-quality.md`.

## Context
On ten Word tasks, two rounds, judged blind, a new document written whole by one python-docx
script scored 4.17 and 4.26 of 5 on design against 3.91 and 3.70 for `write_docx`, with content
and coherence level. The gap repeats only where layout decides (a data table, mixed Chinese and
English, an image with its caption, an open summary): a shaded table header, an East Asian font,
heading styles, page numbers. `write_docx` cannot set any of them. The script route also added
facts the notes did not give (task 01, both rounds), cost 8–19% more and took about 35% longer,
and in the product it would need a Python on the user's machine and an approval per run.

## Decision
- `write_docx` stays the way a new document is written: one markdown source for the whole
  document, compiled (decision 0010). It gains a document style: body fonts for Latin and East
  Asian text, size and spacing, heading look and one accent colour, a table style (shaded bold
  header, bold total row, numbers right-aligned), and a footer with the page number.
- The style is compiled onto real Word styles (Normal, Title, Heading 1–3, a table style), not
  direct formatting, so the user keeps editing in Word with the same styles.
- No style given: a default house style. `template_path` given: the template's styles win.
- The edit tools (`replace_docx_text`, `insert_docx_text`, `delete_docx_text`, `add_docx_chart`,
  `add_docx_image`) stay for a user's own document.
- `run_python_script` is not the route for writing Word documents.

## Consequences
- `write_docx`'s schema changes once (decision 0001): the snapshot and the coordinator text change
  in a reviewed PR.
- The change ships only when it meets the gate on the same ten tasks, against both rounds of this
  test: every check as now, design at least 4.2 on average, content no lower, cost within 10%.
- A document's look changes for every user without a template; their old documents are untouched.
