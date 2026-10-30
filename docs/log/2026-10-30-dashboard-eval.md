# Dashboards made by a real model: six briefs, all working (shipped)

Why: step 2 of `docs/assessments/2026-10-29-design-and-dashboard.md` (#721): does the Dashboard skill
get a model to make a page that works, from the person's own data?

## Shipped
- `evals/dashboard_route.py`: six briefs with a data file each (CSV, an Excel workbook, JSON; one
  in Chinese), four started from the Dashboard tile and two typed in an ordinary conversation. A
  page is read with the app's reader; its `data-figure` and `data-source` names are checked against
  its datasets, its figures against numbers the data gives, figures typed into the page are listed,
  and the page is drawn in Chromium under the app's sandbox policy (script errors, marks drawn,
  empty figures, a screenshot). Checks tested in `tests/test_evals_dashboard_route.py`.
- Dashboard skill: size a chart's margin from its labels and keep value labels off axis labels.

## Measured (DeepSeek flash, effort low, 2026-10-29 off-peak)
- Run 1: 6 of 6 made and working (the skill loaded in each, including the two typed briefs, no
  unknown names, no script errors, every expected figure right: 40 runs and an 85% pass rate,
  9,255 total sales, 20 open tickets, budget 15,100 against 15,360). 0.16 USD.
- Read from the screenshots: KPI cards over d3 charts over a filterable detail table in all six;
  sources and data time shown. Two layout faults: labels overlapping on a horizontal bar chart (06)
  and a negative bar's value label on its axis label (02). After the label rule, briefs 02 and 06
  again: both clean (0.04 USD).
- Left: brief 02's second run shows West's change as "↓ +10.3%" (the sign of a figure the page
  formats itself). The model cannot see its page; step 6 gives it a screenshot.

## Not verified
- Other models; few samples (one or two per brief).
- In the desktop app on Windows.
