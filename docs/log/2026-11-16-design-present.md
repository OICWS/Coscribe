# A Design canvas is presented board by board, and each board has Present and Download PNG (shipped)

Why: a canvas the model makes to show something (options, a flow, a few screens) is shown best
one board at a time; full screen showed one board and had no way to the next. The person also had
to select a board and open the file menu to save it as a PNG.

## Shipped
- The canvas's top-right Play is now **Present**: it fills the panel with the selected board (or
  the first) and steps through the boards in the canvas file's order with Previous / Next, the
  Left / Right arrows and Page Up / Page Down, showing `n / count`. A key pressed inside the
  board's own page stays with that page. Escape or Edit goes back, as before.
- Above each artboard, beside Play: **Present from here** (presents starting at that board) and
  **Download PNG** (the same export as the file menu's Export > PNG, for that board, in the
  scheme the canvas shows). `saveBoard` in `components/design/boardExports.tsx` is shared by both.
- `tests/e2e/design-canvas.spec.ts`: presenting steps forward and back, the buttons disable at
  the ends, Present from here starts at its board; the PNG export test also saves through the
  board's button.

## Not verified
- The PNG export end to end in a cloud container: the server draws the board with the system's
  Chromium (`conversation/page_shot.py`), which timed out there for the existing Export test on
  `main` as well. The board's button was seen to send the same export request.
- The desktop app on Windows.

## Follow-ups
- The rest of the toolbar (text, frame, pen, shapes) and pages: in `docs/plan.md`.
