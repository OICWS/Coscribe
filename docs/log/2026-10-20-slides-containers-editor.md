# The editor selects and edits what a container holds (0018 part 2)

Why: part 1 made containers a thing the engine lays out; the editor numbered a section's elements
by position among its children and so could not follow a section that has one.

## Shipped
- `slide_parts` returns one part per element **as written**, in document order with a container
  before what it holds, each with the box the layout gave it (`Section.nodes`,
  `engine/section_format.py`; the layout reports where each element went, `Laid` in
  `section_layout.py`). A container with a card has a picture of it; one without draws nothing
  (kind `stack`).
- The editor numbers elements the same way (`elementsOf`), takes the box of what a container
  places from its part (`boxOnSlide`), draws it there (`sectionDom.ts`), selects, types into and
  deletes it, and gives a container's place and its children's the layout again after every
  change: a section with a container is read from the server after each save, so what shows is the
  server's layout. A container on the slide moves and resizes like any element.
- What a container places cannot be dragged or resized by hand yet, and Bring forward and Send
  backward are off in a section with a container; its text and the properties panel work.
- Tests: `tests/test_deck_layout.py` (the parts of a section with containers),
  `lib/slideContainers.test.ts`, and, now that there is a DOM for the unit tests,
  `lib/slideTable.test.ts` and `lib/slideTextDom.test.ts` for the table and text panels' functions.

## Checked
- In Chromium against a live server, a slide with a row of three cards: a card's heading restyled
  as Heading 1 grew and pushed its paragraph down inside the card; a card selected and deleted gave
  the other two the room (820 px each).

## Not verified
- Not opened in PowerPoint (plain shapes).

## Follow-ups
- Parts 3 and 4 of 0018: drag in, out and reorder; the container and child panels.
