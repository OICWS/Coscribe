# tools.office.pdf: PDF read, search and write tools

## Purpose
Owns reading and searching a PDF's text with `pypdfium2` (`text.py`), the page fonts used when
writing (`fonts.py`) and `write_pdf`, which renders the shared markdown subset with
`reportlab`. Does not own the page-image conversion (`tools/pdf_pages.py`), Word, Excel or
PowerPoint.

## Public interface
`PdfToolkit`, `build_pdf_tools`, `PDFIUM_LOCK` (the lock around pdfium, shared with `tools/pdf_pages.py`). Import them from `coscribe.tools.office.pdf`; the coordinator
reaches them through `coscribe.tools.office.document_tools`.

## Depends on
`coscribe.runtime`, `coscribe.tools._output_truncation`, `coscribe.tools._thumbnail`,
`coscribe.tools.files`, `coscribe.tools.office.markdown_blocks`, `coscribe.tools.office.table_layout`,
`coscribe.tools.office.toolkit`.

## Invariants
- `pypdfium2` is not thread-safe: every call goes through the lock in `text.py`, which
  `tools/pdf_pages.py` and `pptx` share.
- `reportlab` is imported inside the method that needs it (startup time).

## Tests
`tests/test_documents_tool.py` (the PDF cases).

## Verify by hand
A written PDF with CJK text opened in a real PDF reader on Windows.

## Reviewed
2026-10-17 (first card).
