# A template .pptx can be read for its design (shipped)

Why: the quickest way to make a design system is to start from a company's PowerPoint template.
Its colors could be read, but not its fonts or text sizes, and the model had no one call that
gathered what a design system holds.

## Shipped
- `read_pptx_design(path)`, a deferred, read-only tool: the master theme's 12 colors, its heading
  and body fonts (Latin, East Asian, complex script where set), the master's title, body and other
  text sizes in points and as pixels on a 1920 px slide (what a design system stores), the
  slide size and the layout names. It reads the master only; colors and fonts a slide sets by hand
  are not listed, and the description says so.
- The `design-system` first-message note names it for a `.pptx` the person attached.
- Tests: `tests/tools/office/pptx/test_theme_colors.py`.

## Not verified
- A real company template (stock python-pptx decks only): themes that use scheme-color
  references for text sizes or fonts set on layouts rather than the master.
- A real model turning the result into a good system.

## Follow-ups
- Slide thumbnails of the template saved as a design system's assets, with the assets work.
