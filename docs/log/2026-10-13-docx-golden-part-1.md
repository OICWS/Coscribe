# Golden XML tests for the docx tools, part 1: `write_docx` (shipped)

Why: `tools/documents.py` is to be split into `tools/office/docx/` and `tools/office/pdf/` by pure moves (issue #106, part of #105). Before that, the files its docx tools write get the same golden tests the pptx tools have, so a move can be shown to change nothing.

## Shipped
- `office-agent/tests/test_docx_golden.py` builds 6 documents through `write_docx` (headings and bold/italic runs, bulleted and numbered lists, a table with numeric columns, a table of contents, A4 landscape, CJK text) and compares each with `tests/golden/docx/<name>.txt`. `UPDATE_GOLDENS=1` rewrites them.
- `office-agent/tests/docx_canonical.py` reuses the generic canonicaliser of `pptx_canonical.py` (unchanged) and blanks the values the tools write fresh on every build: `w14:paraId`, `w14:textId` and `w:date` (a tracked change or comment time).
- `_shared.txt` keeps the parts identical in every document once: styles, `stylesWithEffects`, theme, settings, font table, numbering, web settings, `customXml/`, `docProps/app.xml`, the thumbnail and `_rels/.rels`. Styles alone are about 850 KB, so without it each golden would be about 900 KB.
- Stability: the 6 documents were built in two processes with different `PYTHONHASHSEED`, working directories and temp paths; after canonicalising, the goldens are byte-identical.

## Not verified
- On Windows: the Windows workflow runs the whole suite, so it runs these tests. Goldens are written with `\n` and read as text, and nothing in them holds a path.

## Follow-ups
- Part 2: tracked insert, delete and replace, accept all, reject all, an image and a chart.
