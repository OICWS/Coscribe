# Slides editing, part 6a: new, copied, moved and deleted slides (server)

Why: the panel's "+" (new slide with a layout), the thumbnails' Duplicate and Delete, and
dragging a thumbnail to reorder need the deck changed as a whole (design §7, issue #431).

## Shipped
- `tools/office/pptx/engine/view_arrange.py`: `insert_slide` (a section after a slide, or first),
  `duplicate_slide` (right after it, a page copied as a page), `move_slide`, `delete_slide` (the
  last slide stays). A deck's order is its pages' file names, so each renames every page to
  `NN-name` in its new order through temporary names, writes the new one, and builds the deck,
  under the deck's lock and refused when the .pptx changed outside coscribe, as a save is.
- `move_comments`: comments follow their slides to the new names; a deleted slide's go with it.
- `POST /api/threads/{id}/slides/arrange` (`{path, action, index, to?, source?}`) returns the
  index of the slide to show.
- Tests: `tests/test_deck_arrange.py` and the route test.

## Not verified
- A rename on Windows while the page is open in another program (an editor holding the file):
  the rename fails and the request answers that the deck could not be read.
