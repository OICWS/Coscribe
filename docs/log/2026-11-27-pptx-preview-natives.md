# Deck previews draw native charts and tables; figures in Georgia are flagged (shipped)

Why: #1107. In a real financial deck the review saw three slides as blank: the preview of a built
deck drew each native chart and table as a dashed box ("PowerPoint draws it from its data"), the
agent took that for a missing object, redrew the charts as shapes and got two bar heights wrong.
The deck's figures were set in Georgia, whose digits are old-style, so the amounts looked
misaligned; the PPTX Pages skill listed Georgia as a figure font.

## Shipped
- `render_pptx_preview`, the reviewer's pages and every other preview of a deck built from SVG
  pages draw the slide as the Slides panel does (`built_slide_svg` in `engine/build.py`, which
  calls `slide_svg` with pictures left to resvg): charts and tables are drawn from what the build
  wrote, and a template slide's shapes are drawn beneath. `_svg_preview.py` lost its placeholder
  code and its import exception into the engine.
- The deck check warns when a text sets figures in Georgia (`_old_style_figures` in
  `engine/checker.py`), naming the text.
- The PPTX Pages skill and the sections guide no longer offer Georgia for figures; the skill says
  a chart in the preview is drawn from its data and is fixed in its JSON, never redrawn as shapes.

## Not verified
- The preview on Windows with the desktop app; the drawing is the Slides panel's, already in use
  there.

## Follow-ups
- Decision 0012's consequence "native charts and tables are placeholders in its SVG preview" no
  longer holds.
