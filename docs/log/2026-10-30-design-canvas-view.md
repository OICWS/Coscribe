# A Design canvas opens in the panel: artboards to pan, zoom, move and play, and notes (part 2, shipped)

Why: step 4 of `docs/assessments/2026-10-29-design-and-dashboard.md` (#721), after the source and the
server (part 1): the canvas the maintainer showed from Claude's Design.

## Shipped
- `components/design/DesignCanvasPanel.tsx`, opened for a `name.design.json` (loaded on first use):
  each artboard is its own page in a sandboxed frame at its real size, with its title above it, on a
  canvas that pans (wheel, Space-drag, the hand tool) and zooms (Ctrl or Cmd with the wheel, a
  trackpad pinch, −/+; the percentage fits everything). It fits the boards when it opens.
- Toolbar as in the screenshot, first tools: Select (click a board to select it, drag to move it),
  Hand, Note (click to leave a note, double-click to edit, empty text deletes it). Moves and notes
  are saved to the canvas file (`PUT /api/threads/{id}/canvas`).
- Play hands the pointer to the artboards' own pages (their buttons and filters work); Escape or
  the button leaves it.
- `lib/designCanvas.ts`: the canvas types, its routes, and the view math (zoom around a point, fit),
  tested in `designCanvas.test.ts`; `frontend/tests/e2e/design-canvas.spec.ts` (boards drawn, a move
  and a note saved, Play).
- A chip of a canvas opens it like a design.

## Not verified
- In the desktop app on Windows; trackpad pinch.
- Playwright cannot click inside a frame in the scaled canvas (its hit test misreads it), so the
  spec presses the artboard's button from inside the frame; a real pointer was not checked.
- Not yet: frame, pen and shape tools, resizing a board, pages, editing text or variables, a theme
  switch, exports of a canvas (the next steps).
