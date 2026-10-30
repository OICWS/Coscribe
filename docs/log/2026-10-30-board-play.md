# Each artboard plays on its own: on the canvas or full screen (shipped)

Why: one Play for the whole canvas made every board live at once. The person wants to try one
screen where it stands, or one screen filling the panel, and go back to editing that board alone.

## Shipped
- Above each board, next to its title, a Play button opens a menu with two choices:
  - **Play on canvas**: the board takes the pointer where it stands, and its button turns to
    **Edit**. The other boards can still be moved.
  - **Play full screen**: one board fills the panel, fitted to it at no more than its real size.
    **Edit** or Escape goes back.
- The canvas's top-right Play now plays the selected board full screen, or the first board when
  none is selected.
- A link from a played board shows its target played the same way:
  - on the canvas, the target is played and fitted, and the board it came from goes back to
    editing;
  - full screen, the target replaces the board on screen.
- Code: `frontend/src/components/design/BoardPlay.tsx` and `useBoardPlay.ts`. `useBoardLinks.ts`
  now reads which board sent a link from its frame.
- The Design skill's sentences about Play match the new flow.
- `docs/doc-map.toml` now maps the canvas UI to the Design skill.
- e2e: `design-canvas.spec.ts` plays a board on the canvas and full screen, and follows a link;
  all 3 tests pass against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.

## Follow-ups
- A properties panel for a board's page (a layer tree, size, text and CSS): in `docs/plan.md`.
