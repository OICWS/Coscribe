# Deck engine, part 1: SVG pages compile to native PowerPoint shapes (shipped, no tool yet)

Why: decision 0010 (`docs/assessments/2026-10-13-office-route.md`): new decks are compiled from
whole-page SVG sources. This is the compiler; issue #141.

## Shipped
- `office-agent/src/coscribe/tools/_native_svg/`: ppt-master's SVG-element-to-DrawingML emitter
  (commit `bf89859`, MIT), the import closure of its element module plus the text-line and
  inline-geometry pre-passes: 39 modules, ~25k lines, copied as ours. The changes from upstream
  (17 import lines made package-relative, four package `__init__` files emptied, the command-line
  stdout setup removed from one module) are listed in its `NOTICE.md`. Excluded from ruff, mypy,
  the ratchet and the doc-reference check like the other copied code; its 539 KB preset geometry
  file (Apache POI) is on the file-size allow-list.
- `office-agent/src/coscribe/tools/office/pptx/engine/` (ours): `compile_pages(pages, out)` walks
  each page, runs upstream's preflight checks and collects their errors per page instead of
  stopping, converts each element (groups keep their SVG ids as names; translate/scale on
  groups), promotes a full-canvas solid rectangle to the slide background, maps the emitter's
  image and link relationships onto python-pptx's, and makes `<text id="title">` the slide's
  title placeholder (moved out of its group), so `read_pptx` and `edit_pptx_text` see the title.
- `office-agent/tests/test_deck_engine.py` (11 tests) and `tests/golden/engine/basic.txt`. Each
  behaviour was broken once on purpose and its test failed (the text pre-pass, the title, the
  background, the relationship mapping, group translation, the preflight checks).
- The research pages (T1-A) compile to the same look as ppt-master's own exporter, including the
  two-line texts the research spike had joined into one.

- The maintainer opened two compiled decks (the 6-page research deck and the 2-page test deck) in
  PowerPoint on Windows: no repair prompt, every text and shape selectable and editable.

## Not verified
- Rotated, skewed or matrix group transforms, gradient backgrounds, native charts and tables,
  formulas, internal slide links: reported as errors or warnings, not converted yet.

## Follow-ups
- `edit_pptx_text` replaces a title's runs and loses their formatting (bold, size, colour); the
  editing upgrade (phase P2) has to keep run formatting.
- Part 2: the page contract and design guide, the checker and repair loop, the tool(s).
