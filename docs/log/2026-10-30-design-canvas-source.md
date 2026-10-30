# A Design canvas: artboards placed on a canvas, read and placed through the server (part 1, shipped)

Why: step 4 of `docs/assessments/2026-10-29-design-and-dashboard.md` (#721): a Design becomes a canvas
of artboards, as in the front end of Claude's Design the maintainer showed. This part is the source
and the server; the canvas view is the next PR, and nothing opens a canvas yet.

## Shipped
- `conversation/design_canvas.py`: a canvas is `name.design.json` (`boards`: id, title, file, x, y,
  width, height; `notes`) with one self-contained page per artboard in `name.design/`. A board with
  no place goes to the right of the one before it, so a model can list boards and leave the layout to
  the app. `place_on_canvas` moves and resizes the boards named and replaces the notes, keeping every
  other field of the file; a board that is gone is skipped.
- `GET /api/threads/{id}/canvas?path=` (the boards with the paths their pages are served by) and
  `PUT` (what the person did on the canvas). An artboard's page is served by the design route as any
  page is.
- The registry lists a canvas as a `design` named without `.design`; an artboard's page is not
  listed on its own. A card shows the first artboard.
- Rename, copy and delete carry an artifact's side folder for a canvas and for a dashboard as they
  did for a Doc.
- Tests: `tests/test_design_canvas.py`, the canvas routes, the registry and a rename in
  `tests/web/test_artifacts.py`; route and OpenAPI snapshots.

## Not verified
- Nothing draws a canvas yet (the next PR).
