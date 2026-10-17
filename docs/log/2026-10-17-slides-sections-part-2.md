# Slides step 1, part 2: tables, charts, icons, transitions and build-ins in sections (shipped)

Why: a section must say everything an SVG page can before the two are measured against each other
(issue #392, PR 2 of 4; decision 0015).

## Shipped
- `section_objects.py`: tables, charts and icons in a section.
  - **`<table>`** becomes a native PowerPoint table, through the pages' semantic-table JSON.
    - Leading rows of `<th>` are the header; the first header cell's background and colour are
      the header's.
    - `colspan` and `rowspan` merge cells; the cells HTML leaves out are filled in blank, as the
      JSON wants.
    - Per cell: `text-align`, `color`, `background`, `font-weight`.
    - Column widths from `<colgroup><col style="width:Npx"/>`.
    - The table's `font-size`, `font-family`, `color`, `background` and `border-color`.
    - No banding unless the cells say so, so the file shows what the section shows.
  - **`<x-chart>`** holds the pages' chart JSON without its box: the box is the element's style.
    It becomes a native chart whose data the user edits in PowerPoint.
  - **`<x-icon data-icon="ship">`** draws the icon from the pages' icon set in its `color`.
  - The native converters place a frame by its JSON box and size its text by the JSON's px, not
    by the conversion's scale, so the box and `font_size` are converted from the 1920-wide canvas
    before conversion.
- `data-transition` on a section: `fade`, `push`, or `magic` (PowerPoint's Morph, which moves
  elements with the same id from one slide to the next), through the existing
  `set_slide_transition`.
- `data-build-in` on an element: `fade`, `rise` or `pop` (Fade, Rise Up, Zoom entrances), one
  click each in the section's order, through the existing `add_animation_step`.
- `build_deck` builds a folder of `.html` sections as it builds a folder of `.svg` pages. It keeps
  the same `build.json` with a hash per slide, so a deck changed in PowerPoint after its build is
  never overwritten. A folder holds one kind of page; sections are not built on a template.
- Refusals added:
  - attributes on elements inside a table cell, at any depth;
  - child elements inside `img`, `x-icon`, `x-chart` and `x-shape`;
  - attributes on `thead`, `tbody`, `tfoot` and `colgroup`.
- `tests/test_deck_sections_objects.py`: 12 tests.
  - The table's merges, header, cell styles and widths.
  - The chart's data and box, the icon, and both build-ins in order.
  - Morph and Push transitions.
  - Seven refusals.
  - A folder of sections building, and refusing to overwrite a deck changed in PowerPoint.
  - A folder that mixes kinds.

## Not verified
- Morph between two section slides and the three build-ins, played in PowerPoint on Windows.
  The transition and animation XML come from the tools that already write them for edited
  decks.
- The deck order still follows file names. `deck.json` (order, sections, the app's state) comes
  with the panel that edits a deck.

## Follow-ups
- Part 3: `build_pptx_from_pages`'s description covers sections, the "Slides" skill, and the
  evaluation's switch between the two languages.
