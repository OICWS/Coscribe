# End-to-end specs for the Slides properties panels and containers (shipped)

Why: issue #464. The properties panels (text, table, picture and shape, container and child sizing)
and containers (decision 0018) had only unit and DOM tests; `slides.spec.ts` covers select, move,
resize and text.

## Shipped
- `office-agent/frontend/tests/e2e/slides-panels.spec.ts`, one test per case of the issue, run
  against the real server and the stub model: the text panel (size changes the box, a text style
  names it, a size set by hand clears `data-text-style`); a table (type into a cell, rows,
  columns, header toggle); a shape's fill and corner radius; a row container inserted from
  Insert > Shapes (two texts side by side, the gap from the panel, deleting one gives the other the
  row); dragging a text box into a container and out again; Bring forward on a child swapping it
  with its sibling; the comments card closing on a click outside and on Escape (#443). Each step
  checks the saved page or the layout the server read back.
- `slides-helpers.ts` (opening a deck, clicking and dragging in slide coordinates, waiting for the
  editor's save and re-read) and `fixtures/build_section_deck.py` (a deck of three section pages),
  shared by later Slides specs. The spec is in the `SPECS` list of `e2e.yml`.
- Each test was shown to fail by breaking the product code it covers (a panel field doing nothing,
  `moveInto`, `moveOut`, the swap behind Bring forward, the popover's Escape and outside-click
  handlers, the layout's sharing of free room); the breaks are not committed.

## Not verified
- Only Chromium on Linux against the stub model; the Windows desktop app and the Electron panel
  were not run.

## Follow-ups
- A change is saved and then the slide is read again; an edit made in between is shown for a
  moment and then replaced by the read (the next save keeps it). The specs wait for the read
  before the next edit, as a person does. Noted on #464.
