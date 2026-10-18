# tools.office.pptx: PowerPoint tools and the deck engine

## Purpose
Owns the PowerPoint tools: the deck engine that compiles whole-page sources into a deck
(`engine/`), the object tools (shapes, text, images, notes, layouts, themes, animation and
transitions, SmartArt, XML-level edits and review), reading a deck and the QA checks (`qa.py`).
`presentations.py` and `pptx_templates.py` in `tools/`, and `_pptx_*`, `_svg_*`, `_native_*`
there, belong here too until they move. Does not own Word, Excel or PDF, or how the viewer draws
a deck.

## Public interface
`NEW_DECK_INSTRUCTIONS`, `PresentationToolkit`, `build_legacy_presentation_tools` (the tools that still live in
`tool_wrappers.py`, for `tools/presentations.py`), `build_presentation_tools`; for the Slides panel, `read_deck`, `slide_svg`, `NotBuiltFromPages` its downloads `deck_pdf`, `deck_html`, `deck_basic_fonts`, and its comments `read_comments`, `add_comment`, `reply_to_comment`, `resolve_comment`, `delete_comment`, `CommentNotFound`; its edits `slide_parts`, `save_slide`, `add_slide_asset`, `SlideChanged`, `SectionError`, `DeckChangedError`. Import them from `coscribe.tools.office.pptx`.

## Depends on
`coscribe.runtime`, `coscribe.tools._chart_data`, `coscribe.tools._file_locks`,
`coscribe.tools._native_formula`, `coscribe.tools._native_svg`, `coscribe.tools._office_com`,
`coscribe.tools._ooxml_validate`, `coscribe.tools._output_truncation`, `coscribe.tools._pptx_shapes`,
`coscribe.tools._pptx_text`, `coscribe.tools._svg_slide`, `coscribe.tools._thumbnail`,
`coscribe.tools._workspace`, `coscribe.tools.office.markdown_blocks`, `coscribe.tools.office.pdf`,
`coscribe.tools.pptx_templates`.

## Invariants
- Office files are compiled from whole-page sources
  (`docs/decisions/0010-office-files-are-compiled-from-whole-page-sources.md`); every design
  decision is numbered in `office-agent/PPTX_DESIGN.md`, read it before changing a tool.
- Tool schemas are fixed and snapshotted (`tests/tool_schemas.txt`); a wrapper change must not
  change them.
- Every write is validated against the OOXML schemas before the file is touched.

## Tests
`tests/tools/office/pptx/` (the tool tests, one file per concern: layouts, charts, animation,
templates, ...; shared builders in `helpers.py`), `tests/test_deck_engine*.py`,
`tests/test_pptx_*.py`, `tests/test_office_golden.py` (XML goldens), `tests/test_evals_pptx.py`.

## Verify by hand
A generated and an edited deck opened in the real PowerPoint on Windows: fonts, charts,
animation and transitions.

## Reviewed
2026-10-17 (first card).
