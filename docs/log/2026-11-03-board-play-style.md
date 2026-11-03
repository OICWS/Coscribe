# A board's Play button is quiet and stands off the board (shipped)

Why: the maintainer found the Play button above each artboard ugly and too large: an outlined
uppercase "PLAY" taller than the title, about 6 px above the board.

## Shipped
- **Play:** a small "▷ Play" in sentence case, muted, with no border. A light fill shows on
  hover and while its menu is open.
- **Edit:** the same size, filled with the accent colour, while a board is played.
- **Menu:** its items are a step smaller, to match the button.
- **Spacing:** the title row stands 10 px above the board (it was 6 px).
- Code: `frontend/src/components/design/BoardPlay.tsx` and `CanvasParts.tsx`.
  `design-canvas.spec.ts` passes 4 of 4 against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
