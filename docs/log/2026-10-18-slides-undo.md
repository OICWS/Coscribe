# Slides editing, part 7: undo and redo, coscribe's builds included

Why: Undo and Redo in the zoom menu were shown but not available; the design makes one change of
coscribe's one undo step, like one of the user's (§9, issue #431).

## Shipped
- `tools/office/pptx/engine/history.py`: every build of a deck records its pages and comments
  under the pages folder's `.history/`, labelled "coscribe" (the model's builds) or "you" (the
  panel's saves, inserts, notes, properties and slide changes); a state equal to the last is not
  recorded again, and 50 are kept. Before a change from the panel the pages are recorded as they
  are, so a deck built before this, or pages coscribe wrote without building, can be undone too.
- `deck_history` and `step_history` (`view_history.py`): undo puts the previous state's pages
  back and builds the deck; redo the next one. A change after an undo drops the undone states.
  Refused when the .pptx changed outside coscribe, as every change from the panel is.
- `GET` and `POST /api/threads/{id}/slides/history` (`{path, action: "undo" | "redo"}`).
- The panel: Undo and Redo in the zoom menu ("Undo coscribe's change" when the step is the
  model's), Ctrl+Z, Ctrl+Shift+Z and Ctrl+Y outside text being typed.
- Tests: `tests/test_deck_history.py`.

## Checked
- In Chromium against a live server: slide 2's title moved (the page became a section), undone
  from the menu (back to the SVG page), redone with Ctrl+Shift+Z.

## Not verified
- coscribe is not told that its change was undone; it reads the pages as they are on its next
  turn. Telling it, with the user's own edits, is the open item in `docs/plan.md`.
