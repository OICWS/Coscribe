# A Dashboard is a page and its datasets, served with the data and d3 (shipped)

Why: step 1 of `docs/assessments/2026-10-29-design-and-dashboard.md` (#721). Dashboard was a "Soon"
tile; the maintainer chose d3 for its charts.

## Shipped
- `conversation/dashboard.py`, beside the artifact registry: an `.html` page with `<meta name="coscribe" content="dashboard">` in its head
  is a dashboard; `name.dashboard/datasets.json` names its datasets (source, updated, columns) and
  figures (value, formula), `name.dashboard/data/<id>.json` holds the rows (objects, or columns and
  rows). `render_dashboard` puts `window.coscribe` (datasets with rows, figures, or the reason the data
  could not be read) first in the head, and d3 where the page has `<script data-coscribe-lib="d3">`.
  JSON cannot close its script early. 8 MB cap on the data.
- d3 7.9.0 (ISC) vendored in `conversation/_vendor/` with its licence.
- The design route serves a dashboard with its data under the same sandbox policy, so the panel,
  the card and Export HTML (one self-contained file) work as for a design.
- The registry lists a marked page as kind `dashboard`; `list_artifacts` takes the kind.
- The Dashboard tile is enabled ("New") with its placeholder, and its first message carries a note
  that names the new built-in skill `Dashboard` (files, datasets, figures, placeholders filled from
  `window.coscribe`, d3 charts, layout, refresh, checks before done).
- Tests: `tests/test_dashboard.py`, the route and kind in `tests/web/test_artifacts.py`, the note,
  the built-in skill lists; tool schema snapshot regenerated on 3.11.

## Checked by hand
- A hand-written dashboard following the skill, served under the sandbox policy in Chromium: the
  figures fill in, d3 draws 7 bars, no script errors.

## Not verified
- Not run with a real model yet (step 2).
- Not on Windows or in the desktop shell.
- The panel redraws when the page is written, not when only its data files are; a refresh that
  rewrites only data needs the panel reopened until step 3.
- A chip and the panel still call a dashboard a design (they read the path, not the kind).
