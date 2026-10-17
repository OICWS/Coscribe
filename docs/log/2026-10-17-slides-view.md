# Slides panel, part A: a built deck's slides, each drawn as one SVG (shipped, unused)

Why: the Slides panel shows an unedited slide as its SVG page, drawn as an image (decision 0016).
A page alone does not show what the user gets: its charts and tables are JSON, its icons and
pictures point elsewhere, and its notes and transition can be changed in the .pptx (issue #420,
PR 1 of 3).

## Shipped
- `tools/office/pptx/engine/view.py`:
  - `read_deck(deck)` lists the slides of a deck built from pages. Each slide has its page name,
    its kind (page or section), and its notes, transition and background from the built .pptx.
    `changed` says the .pptx or a page differs from what the last build saw.
  - `slide_svg(deck, index, workspace)` gives one SVG with nothing outside it. Icons are drawn,
    pictures inside the workspace are inlined, and native charts and tables are drawn.
    Scripts, event attributes and outside links are dropped: the SVG is served from the app's
    origin.
- `engine/view_native.py` draws the native objects from what the build wrote:
  - tables from their cells, with fills, borders, runs and wrapping, rows growing as in PowerPoint;
  - column, bar, line, area, pie and doughnut charts from the cached values and colours;
  - other chart types as a labelled box.
- `web/routes/slides.py`: `GET /api/threads/{id}/slides?path=` and
  `GET /api/threads/{id}/slides/{index}/svg?path=`. A deck not built from pages answers 409. The
  SVG carries a `default-src 'none'` content policy.
- Tests: `tests/test_deck_view.py` (4) and a route test in `tests/web/test_thread_activity.py`.

## Checked
- The evaluation's 15-slide bilingual deck (task 14): its column chart with per-bar colours and
  its five-row table draw as the build wrote them.

## Not verified
- The drawing next to PowerPoint's on Windows. The chart drawing is close, not exact: axis label
  sizes and gaps follow PowerPoint's defaults, not its layout engine.

## Follow-ups
- Part B, the panel; part C, present and export.
