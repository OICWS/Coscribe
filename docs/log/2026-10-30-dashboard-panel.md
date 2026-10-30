# A dashboard shows where each figure came from, and its panel refreshes it (shipped)

Why: step 3 of `docs/assessments/2026-10-29-design-and-dashboard.md` (#721): every number shows where
it came from, and the data can be made again.

## Shipped
- `conversation/dashboard_sources.js`, put at the end of every dashboard the app serves: hovering an
  element bound with `data-figure` or `data-source` shows a small "i"; clicking it opens a box with
  the figure's label and formula and, for each dataset it comes from, its title, source, time and row
  count. It is the page's own script, so it works the same in the panel and in an exported HTML file.
- `GET /api/threads/{id}/dashboard?path=`: a dashboard's datasets (title, source, updated, rows);
  404 for a page that is not one.
- The panel of a dashboard says when its data was made (the oldest dataset's time, the sources in
  its tooltip) and has Refresh, which asks coscribe in the conversation to read the sources again
  and rewrite the data, leaving the page as it is.
- Tests: the route and the script's place in the served page (`tests/web/test_artifacts.py`), and
  `frontend/tests/e2e/dashboard.spec.ts` (data time, the box with formula and source inside the
  frame, Refresh sending its message); route and OpenAPI snapshots.

## Corrected
- The step 1 log said the panel did not redraw when only the data files changed: it does, since the
  panel redraws after every tool call of a turn. A refresh made outside a turn (a scheduled task,
  later) still needs the panel reopened.

## Not verified
- In the desktop app on Windows.
- The "i" box is light in a dark page.
