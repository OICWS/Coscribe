# The Design skill writes canvases, and a canvas's variables are its design system (shipped)

Why: step 5 of `docs/assessments/2026-10-29-design-and-dashboard.md` (#721). The canvas can be
opened and arranged now, so coscribe should write canvases: several artboards (options, sizes) on
one canvas, sharing one set of design variables the person can change in one place.

## Shipped
- The skill `svg-design` ("SVG and HTML Design") is now `design` ("Design"): when a Design is the
  right output (a deck is Slides, real data a Dashboard), the canvas file and one page per artboard,
  artboard sizes (desktop, laptop, tablet, phone, A4 poster, social square, story, link preview),
  options as numbered artboards, the same screen at several sizes, real content, what a page may
  hold, how to change a design without losing the person's moves and notes, and the icon-sheet
  rules as one part.
- A canvas declares `variables` (`name` a CSS custom property, `value`, `label`). The design route
  puts them last in the head of each artboard's page, so the canvas's value wins over a page's own:
  the variables are the design system all artboards share. A value that could end the declaration,
  the rule or the style element, or open a comment, is dropped. `PUT /api/threads/{id}/canvas`
  takes `variables` (name to value) for the panel to set them; only declared ones change.
- The first-message note of a Design start names the Design skill and the `.design.json` canvas.
- `evals/design_route.py`: six briefs (four from the tile, one in Chinese), the canvas read by the
  app's reader, boards' pages and variables checked, every artboard drawn at its size in Chromium
  as the app serves it, for script errors, blocked loads and overflow; its checks tested in
  `tests/test_evals_design_route.py`. Not run yet (off-peak).
- Tests: variables (parsed, unsafe ones dropped, set by placing) in `tests/test_design_canvas.py`;
  the served page and the PUT in `tests/web/test_artifacts.py`; skill name lists; OpenAPI snapshot.

## Not verified
- No model has written a canvas with this skill yet: the DeepSeek run of `evals/design_route.py`
  goes off-peak.
- The panel does not show or edit the variables yet (the next PR).

## Follow-ups
- Variables and text editing in the canvas panel; a Design start that names a library design system
  (today only Slides takes one); the Design eval; `look_at_page` for both skills.
