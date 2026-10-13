# Golden XML tests for the docx tools, part 2: tracked edits, image, chart (shipped)

Why: second half of issue #106 (part of #105). Part 1 covered `write_docx`; this covers the tools that edit a document after it is written, so the split of `tools/documents.py` can be shown to change nothing for them too.

## Shipped
- 7 more documents in `office-agent/tests/test_docx_golden.py`, each built on the `headings_and_runs` document: `tracked_insert`, `tracked_delete` (across a bold and an italic run), `tracked_replace`, `accepted_changes` and `rejected_changes` (insert, delete and replace, then accept or reject all), `image` (with a caption), `chart` (bar chart after a heading, with a title and caption).
- The chart's embedded workbook is canonicalised member by member, with its `docProps/core.xml` timestamps blanked.
- The image is a committed PNG (`tests/golden/docx/assets/logo.png`), not drawn at test time, because a PNG's bytes depend on the encoder and zlib.
- The `w:date` of each tracked change is blanked by `docx_canonical.py` (part 1); it is a build time.
- Stability: all 13 documents built in two processes with different `PYTHONHASHSEED`, working directories and temp paths give identical goldens.

## Not verified
- On Windows: the Windows workflow runs the whole suite, so it runs these tests.

## Follow-ups
- Merging `docx_canonical.py` into `pptx_canonical.py` (a later cleanup, once the xlsx work has landed too).
