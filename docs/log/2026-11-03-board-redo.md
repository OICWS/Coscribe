# The properties panel's edits can be redone, and undo survives a reload (shipped)

Why: the panel's Undo (`docs/log/2026-11-03-board-undo.md`) counted only the edits made since the
canvas was opened, so after a reload it started disabled. There was also no way to take back an undo.

## Shipped
- **Redo** sits next to Undo in the panel's header. It writes the last undone edit back.
  **Ctrl+Shift+Z** or **Ctrl+Y** (Cmd on a Mac keyboard) does the same outside a field.
- **The buttons ask the server.** `GET /api/threads/{thread_id}/canvas/element/steps?page=` says
  how many steps there are to undo and redo on the page as it is now. The panel asks again after
  every save and whenever coscribe writes the page, so Undo works after a reload.
- How it works (`conversation/board_undo.py`):
  - Each page keeps two lists of sources, one to undo and one to redo, and a hash of the page as
    the panel last left it.
  - A new edit clears what there was to redo.
  - When the page was written since (by coscribe or anything else), there are no steps. Undo or
    redo refuses and drops them, so that work is not lost.
- **Next turn:**
  - A redo of an undo coscribe was not told of cancels out of the note.
  - Otherwise the edit is reported again.
- **Route:** `POST /api/threads/{thread_id}/canvas/element/redo`. Undo and redo both answer with
  the steps left.
- **Tests:**
  - `tests/test_board_edits.py`: step counts, undo and redo, what the note says, and a new edit
    clearing redo.
  - The canvas route test.
  - `design-canvas.spec.ts` redoes with the button, reloads, and then undoes with the button.
    All 4 tests pass against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
