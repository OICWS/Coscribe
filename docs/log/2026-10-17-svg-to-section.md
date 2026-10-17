# Slides step 2, part 1: an SVG page converts to a section with its content unchanged (shipped, unused)

Why: decision 0016 keeps new slides as SVG pages and turns a slide into a section when the user
first edits it; nothing on the slide may move or change in that conversion (issue #414, PR 1 of 2).

## Shipped
- `tools/office/pptx/engine/svg_to_section.py`, `convert_page(svg) -> (section, kept)`.
  - **Text becomes text boxes.** Each text is converted by the pages' emitter, and its box, runs,
    faces, sizes, colours, alignment, spacing and line breaks are read back. The box does not
    wrap (`white-space: nowrap`), because the page's lines are where its author put them. Spaces
    HTML would collapse are kept as no-break spaces.
  - **Everything else stays SVG.** Each top-level shape or group, without its texts, becomes an
    `<svg>` element cropped to its bounds and drawn by the same emitter. A card's texts come out
    over its shapes.
  - **Other elements**:
    - native charts and tables become `x-chart` and `table` (band fills written per cell);
    - pictures become `img`;
    - icons become `x-icon`;
    - the full-page rectangle becomes the background;
    - `desc id="notes"` becomes `aside`;
    - the title stays the title.
  - **What cannot be said exactly stays SVG, and is listed**: rotated text, text that is not one
    solid colour, a table with uneven rows. A slide on a template is refused.
- The section language gains `line-height: normal` (the face's own single spacing, which the
  emitter uses for one-line texts), `letter-spacing`, `white-space: nowrap`, and `font-family` on a
  span. Only ASCII white space collapses.
- `tests/test_svg_to_section.py`: 5 tests.
  - Three pages (the engine's cover and cards, and a page with a chart, a table, a picture, an icon,
    notes and a background) compile to slides with the same texts, runs and alignment points, and
    the same box for every other shape. Moving one text by a pixel fails the test.
  - Texts become editable boxes, kept spaces, rotated text kept as a drawing, template refused.

## Checked
- The decks the evaluation made on the SVG route for tasks 01, 04 and 09 (15 slides), each slide
  converted and compiled both ways:
  - every text at the same place (0.0 px);
  - every other shape at the same box;
  - LibreOffice renders identical (0.00% of pixels differ).
- Two fixes came from this check. A box that wrapped broke "12,710" in two under a substituted
  font, so converted boxes do not wrap. A widened box moved left-aligned text, so the box keeps the
  emitter's width.

## Not verified
- PowerPoint on Windows. The XML of the two compiled decks matches, so it should look the same.

## Follow-ups
- Part 2: folders that mix `.svg` and `.html` slides, and converting one slide of a built deck.
