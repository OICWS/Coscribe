# Slides editing, part 2: the edit API

Why: the editor needs one slide in a form it can place element by element, and a way to save it
back as a section and rebuild the deck (issue #431, design §3, decision 0016).

## Shipped
- `tools/office/pptx/engine/view_edit.py`:
  - `slide_parts(deck, index, workspace)`: the slide's section source, its version (the hash of
    its file), and per element its box on the 1920 × 1080 canvas and, for everything but text, a
    picture of that element alone (an SVG data URI with 24 px of room around the box, so strokes
    and labels are not cut). An SVG page is read as the section it converts to; nothing is
    written.
  - `save_slide(deck, index, source=, version=, resource_root=)`: checks the section, then under
    the deck's lock refuses when the slide's file is not the version read (`SlideChanged`) or the
    .pptx changed outside coscribe (`DeckChangedError`), writes the section (an SVG page becomes
    the section then, and its .svg is removed), and builds the deck. Returns the new name and
    version and what the build found on that slide (text that does not fit, ...).
- `GET /api/threads/{id}/slides/{index}/parts` and `PUT /api/threads/{id}/slides/{index}/source`
  (`{path, source, version}`): 409 with `changed: "slide"` or `"deck"` and a fixed message, 400
  for a section the language refuses.
- `section_drawing` can report which drawn elements belong to which element of the section.
- Tests: `tests/test_deck_edit.py` (parts of a section and of a chart slide; an SVG page read
  without being changed; a save that converts and rebuilds; refusals), and a route test.

## Not verified
- Saving while coscribe builds the same deck: both take the deck's lock, but only the engine
  tests exercise it, not a live turn.
