# documents.py is now tools/office/{docx,pdf} (shipped)

Why: decision 0010 puts each office format in its own package under `tools/office/`, so the Word phase works inside a small package. `tools/documents.py` (1,928 lines) was the first of the two big files to move. Part of #147.

## Shipped
- A pure move, split by line range: the function and class bodies are unchanged.
- `tools/office/markdown_blocks.py`: `Block`, `parse_blocks`, `parse_inline_runs`, the comment marker and the pipe-table row helpers (the old `tools/_markdown_tables.py` is folded in and gone).
- `tools/office/table_layout.py`: the column-width measuring that docx and pdf share.
- `tools/office/toolkit.py`: `WorkspaceToolkit`, the scope checks both toolkits start from.
- `tools/office/docx/`: `DocxToolkit` (the methods), `_xml.py` (the hand-built OOXML helpers), `tools.py` (`build_docx_tools`, the nine tool functions with their docstrings).
- `tools/office/pdf/`: `PdfToolkit`, `text.py` (pdfium page text and its lock), `fonts.py` (the CJK font), `tools.py` (`build_pdf_tools`).
- `tools/office/document_tools.py`: `DocumentToolkit(DocxToolkit, PdfToolkit)` and `build_document_tools`, which returns the docx tools then the pdf tools in the old order.
- Imports updated in `tools/__init__.py` (now also exports `DocumentToolkit`, so `session.py` imports it from the package), `presentations.py`, `pdf_pages.py`, `_chart_data.py`, `spreadsheets.py`; path mentions in comments and docs follow.

## Checked
- `tests/tool_schemas.txt`, `tests/web_routes.txt` and the docx goldens are byte-identical; tests changed only in import lines.
- `lint-imports` and mypy pass.
- `quality/baseline.json`: `documents.py` and `build_document_tools` (434 lines) are gone; `write_docx` (complexity 18) and the docx tool list (now `build_docx_tools`, 371 lines) appear under their new names with no larger number. `ratchet.py --update` refuses a renamed entry as "new", so the file was written with `--accept-worse`; the diff shows only renames and two improvements.

## Not verified
- The Windows CI job was not run locally.

## Follow-ups
- PR 2 of #147 moves `spreadsheets.py` to `tools/office/xlsx/`.
