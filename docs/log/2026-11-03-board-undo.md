# The properties panel's edits to an artboard can be undone (shipped)

Why: the edits the properties panel writes into a page (`docs/log/2026-11-02-board-edits.md`)
could only be taken back by editing the value again or by asking coscribe.

## Shipped
- **Undo** sits in the panel's header. It takes back the panel's last edit to the selected
  board's page, one step at a time. **Ctrl+Z** (or Cmd+Z) does the same outside a field; inside a
  field it still undoes the typing.
- After an undo the board is served anew and the same element is picked again.
- How it works (`conversation/board_undo.py`):
  - Before each edit, the page's source is kept, with a hash of what the edit wrote. Up to 20
    steps are kept per page.
  - Undo puts the kept source back only while the page is still exactly what the panel wrote.
  - When coscribe or anything else has written the page since, undo refuses, so that work is not
    lost, and the kept steps for that page are dropped.
- **Next turn:**
  - An undone edit coscribe was not yet told of is dropped from the next turn's note.
  - One it was told of is reported as undone ("undid …").
- **Route:** `POST /api/threads/{thread_id}/canvas/element/undo` answers with fixed messages
  when there is nothing to undo or the page was written since.
- **Tests:**
  - `tests/test_board_edits.py`: step-by-step undo; the note when the edit was or was not yet
    told; a page written since is not put back.
  - The canvas route test.
  - `design-canvas.spec.ts` undoes two edits, one with the button and one with Ctrl+Z, and the
    file is byte for byte what it was. All 4 tests pass against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
- The Undo button counts the edits made since the canvas was opened. The server keeps up to 20
  steps across reloads, but after a reload the button starts disabled.

## Follow-ups
- Redo.
- The Code tab editable.
