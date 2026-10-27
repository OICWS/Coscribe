# tools.office.docx: Word (.docx) read, write, edit and review tools

## Purpose
Owns the Word tools and their toolkit: reading a document as markdown, writing one from the
shared markdown subset, structure edits (headings, tables, styles, TOC; `_structure.py`,
`_style.py`), tracked-change edits and the review tools (`_review.py`), and the raw XML helpers
(`_xml.py`), and a document as blocks for the Docs editor with a save that rewrites only the changed blocks (`blocks.py`), the pictures it shows and adds (`block_images.py`), divider and page-break paragraphs (`block_breaks.py`), how a paragraph, run and table cell look once styles and direct formatting are resolved (`look.py`, `block_tables.py`: display only, a save never writes a paragraph's look back). The tool wrappers (names, parameters, docstrings the model sees) are in `tools.py`, the
implementation in `toolkit.py`; a changed signature also changes `tests/tool_schemas.txt`. Does not own PDF, Excel or PowerPoint, the shared markdown blocks and table
layout (`tools/office/`), or how the viewer panel draws a document (`web/`, `frontend/`).

## Public interface
`DocxToolkit`, `build_docx_tools`, and for the Docs editor (decision 0019, `blocks.py`) `read_doc_blocks`, `read_doc_image`, `save_doc_blocks`, `DocChanged`, `BlocksRefused`, and what the person changed since coscribe was told (`user_edits.py`) `remember_before_edit`, `edits_since_told`, and the versions the editor has held, to undo a change made behind it (`history.py`) `remember_version`, `restore_version`, `VersionGone`, and `docx_from_markdown`, a Word file made of the writer's markdown as bytes, for an export. Import them from `coscribe.tools.office.docx`; the coordinator
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
`tests/test_docx_golden.py` (canonical XML goldens), `tests/test_docx_blocks.py` (the editor's reader and writer), `tests/test_docs_edits_note.py` (what the person changed, told once), `tests/test_docx_history.py` (the kept versions and the undo), `tests/test_evals_docx.py`.

## Verify by hand
A written and an edited document opened in the real Word on Windows, tracked changes shown and
accepted there.

## Reviewed
2026-10-17 (first card).
