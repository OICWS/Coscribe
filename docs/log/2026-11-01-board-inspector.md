# The canvas shows an artboard's elements and their style, read only (shipped)

Why: step 1 of the properties panel in `docs/plan.md`. The person wants to see what an artboard is
made of and why it looks as it does, before editing it there.

## Shipped
- **Properties** in the canvas's top-right bar opens a panel beside the canvas.
- A click on a board, without dragging it, selects the board and picks the element under the
  pointer. The element gets an outline on the board.
- The panel shows the board's elements as a tree. Each row names its kind (Page, Row, Column,
  Grid, Text, Image, Frame) and its text. A row picks its element too.
- For the picked element, the panel has two tabs:
  - **Properties**: its size, then layout, text and fill, leaving out values that say nothing
    (`normal`, `none`, `0px`).
  - **Code**: the style rules that match it, with the shorthands the page was written with, and
    what it inherits, grouped by ancestor ("From <body>").
- How it reads the page: an artboard's frame is sandboxed without same-origin, so the app cannot
  read its page. Each artboard is served with a small script that answers the panel's questions
  by message, and only to its own parent (`conversation/board_inspector.js`, beside
  `BOARD_LINKS`). It changes nothing in the page.
- Frontend files: `components/design/BoardInspector.tsx`, `useBoardInspector.ts`,
  `lib/boardInspector.ts`.
- Tests:
  - `design-canvas.spec.ts` picks an element on the board and in the tree, and reads its size,
    rule and inherited font (all 4 tests pass against a live server).
  - `boardInspector.test.ts`.
  - `test_design_canvas.py` checks the script is served with each artboard and holds no closing
    tag.
  - `look_at_page`'s real-browser tests still pass with the script in the page.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
- A page with more than 400 elements shows the first 400 in the tree.

## Follow-ups
- Step 2: edit text and a few properties (size, font size, colour) and write them back to the
  page; tell coscribe at its next turn what the person changed, as for slides.
