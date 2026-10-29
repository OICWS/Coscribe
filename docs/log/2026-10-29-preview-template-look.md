# The Slides panel draws a template deck's look under its pages (shipped)

Why: a deck built on the maintainer's template showed bare pages in the panel and on the cards: no
teal diagonals, no logo, no brand mark. PowerPoint showed all of them. The template's look lives in
the slide master, the layout and the shapes a page takes over from a template slide
(`data-template-slide`). The panel drew only the page.

## Shipped
- `engine/view_template.py` draws the slide's background, the master's and the layout's own
  shapes (unless hidden) and the shapes taken over from a template slide, as SVG under the page.
  The subset: preset rectangles, rounded rectangles, ellipses, triangles, diamonds,
  parallelograms, pentagons and chevrons; custom paths (lines, Béziers, arcs); pictures with
  crop; groups; rotation and flips; solid, theme (with lumMod/lumOff/tint/shade/alpha),
  linear-gradient and picture fills; outlines; one line per text paragraph. Anything else is left
  out, not drawn wrong.
- The build records how many shapes each page took over from a template slide
  (`template_shapes` in `build.json`), so the view knows which shapes they are.
- Fixed with it: a table taken over from a template slide threw the pairing of the page's native
  tables and charts with their drawings off by one.
- Checked against LibreOffice's render of a test template (freeforms, gradient, rotated circle,
  logo, footer text): the same picture apart from the page's fonts.

## Not verified
- The maintainer's own template. Wrapped body text in a template shape is drawn as one line per
  paragraph.
- Card speed: each slide picture still opens the .pptx once. Not changed here.
