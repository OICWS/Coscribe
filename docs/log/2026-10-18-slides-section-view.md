# Slides editing, part 1: a section slide drawn by the server

Why: a slide that is a section (an edited slide, decision 0016) showed blank in the panel's
thumbnails and Present, and the web page and drawn PDF downloads left it out. Editing turns slides
into sections, so they must be drawn first (issue #431).

## Shipped
- `tools/office/pptx/engine/section_view.py`: a section as one SVG on the 1920 × 1080 canvas, in
  the section's order:
  - shapes, pictures and embedded drawings are the SVG the compiler already makes for them;
  - text is broken into lines by the same rules and advances the checks measure with
    (`text_layout.lines`, which agrees with `line_count`), aligned and anchored in its box;
    bullets and numbers are drawn beside list items;
  - charts and tables are drawn from the built slide, as for the SVG pages.
- `slide_svg` serves a section slide too; the web page and the drawn PDF include every slide.
- The panel draws a section's thumbnail and its slide in Present from that image.
- Tests: `tests/test_deck_view_sections.py` (a section's text, shapes and picture; a table, chart
  and icon; wrapped text; lines agree with the measured count; downloads of a mixed deck).

## Checked
- The three section fixtures drawn through resvg and looked at: text, the band, the photo, the
  embedded bars, the table, the chart and the icon in their places.

## Not verified
- Line breaks against PowerPoint's own on Windows: they follow the estimated advances, so a line
  can break a word earlier or later than PowerPoint does.
