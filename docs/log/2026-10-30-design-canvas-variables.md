# The canvas panel edits a design's variables and shows its artboards light or dark (shipped)

Why: step 5 of `docs/assessments/2026-10-29-design-and-dashboard.md` (#721). A canvas's variables
are the design system its artboards share (`2026-10-30-design-skill-canvas.md`); the person should
change them in one place and see every artboard follow, and see a design in both schemes.

## Shipped
- A Variables button on the canvas (shown when the canvas declares any) opens a panel with one row
  per variable: a colour gets a swatch as well as its text. A value is saved when its field is left
  or Enter is pressed (a swatch a moment after it stops changing), through the canvas PUT, and every
  artboard reloads with it.
- Light or dark: the server serves an artboard in the scheme asked for (`scheme=light|dark` on the
  design route). A frame cannot set the `prefers-color-scheme` a sandboxed page sees, so the page's
  own queries are answered in its text (styles and scripts) and `data-theme` is set on its root;
  `in_scheme` in `conversation/design_canvas.py`. The skill says to give a page its dark look in
  either form.
- Tests: `in_scheme` and the route's `scheme` in `tests/test_design_canvas.py` and
  `tests/web/test_artifacts.py`; `asHexColour` in `designCanvas.test.ts`; e2e
  `design-canvas.spec.ts` sets a variable from the panel and sees the artboard's colour change and
  the file hold it, then switches to dark and sees the page's dark background.

## Not verified
- On Windows in the desktop app (run in Chromium here, in the e2e spec).
- No model has written a canvas with variables yet; the Design eval runs off-peak.

## Follow-ups
- Edit an artboard's text in place; a Design start that names a library design system.
