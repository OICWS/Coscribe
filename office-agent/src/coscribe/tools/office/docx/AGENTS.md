# tools.office.docx: Word (.docx) read, write, edit and review tools

## Purpose
Owns the Word tools and their toolkit: reading a document as markdown, writing one from the
shared markdown subset, structure edits (headings, tables, styles, TOC; `_structure.py`,
`_style.py`), tracked-change edits and the review tools (`_review.py`), and the raw XML helpers
(`_xml.py`). Does not own PDF, Excel or PowerPoint, the shared markdown blocks and table
layout (`tools/office/`), or how the viewer panel draws a document (`web/`, `frontend/`).

## Public interface
`DocxToolkit`, `build_docx_tools`. Import them from `coscribe.tools.office.docx`; the coordinator
reaches them through `coscribe.tools.office.document_tools`.

## Depends on
`coscribe.runtime`, `coscribe.tools._chart_data`, `coscribe.tools._docx_chart`,
`coscribe.tools._file_locks`, `coscribe.tools._native_docx_tracks`, `coscribe.tools._ooxml_validate`,
`coscribe.tools._output_truncation`, `coscribe.tools._thumbnail`, `coscribe.tools.office.markdown_blocks`,
`coscribe.tools.office.table_layout`, `coscribe.tools.office.toolkit`.

## Invariants
- A write is validated against the ECMA-376 schema before the file is touched, so a bad edit
  raises instead of producing a file Word repairs (`_ooxml_validate`).
- Heavy libraries (`mammoth`, `python-docx`, `markdownify`) are imported inside the method that
  needs them, not at module level (startup time); tool signatures name no library type.
- A Word document gains a document style, not a script route
  (`docs/decisions/0013-word-documents-gain-a-document-style-not-a-script-route.md`).
- `_review.py` and the review tools are being changed by #343.

## Tests
`tests/test_documents_tool.py`, `tests/test_docx_structure_tool.py`, `tests/test_docx_review_tool.py`,
`tests/test_docx_golden.py` (canonical XML goldens), `tests/test_evals_docx.py`.

## Verify by hand
A written and an edited document opened in the real Word on Windows, tracked changes shown and
accepted there.

## Reviewed
2026-10-17 (first card).
