---
name: Dashboard
description: Make a dashboard, a page of the person's real data (figures, charts, a table, filters) the app opens in its Dashboard panel and that can be refreshed when the data changes -- load before making or refreshing one. A mock-up with made-up numbers is a Design; one chart in a document is a Doc.
---
A dashboard is a page and its data, kept apart. The page draws; it writes no figure itself. The
data sits in a folder beside it, and the app puts it into the page when it shows it. The page is
drawn in a sandboxed frame with no network: no CDN, no web fonts, no remote images, no fetch.

## The files

For a dashboard named `test-results`:

    test-results.html            the page
    test-results.dashboard       a folder beside it, holding
      datasets.json              what each dataset is and where it came from
      data                       a folder with one file per dataset, its rows:
        runs.json

`datasets.json`:

    {
      "datasets": {
        "runs": {
          "title": "Test runs",
          "source": "reports/ci-2026-10-28.csv",
          "updated": "2026-10-28T08:10:00",
          "columns": ["scenario", "result", "minutes"]
        }
      },
      "figures": {
        "pass_rate": {
          "label": "Pass rate",
          "value": 0.938,
          "formula": "runs where result = pass / all runs",
          "from": ["runs"]
        }
      }
    }

- `source` says where the rows came from: a file path, a connector and its query, or the script
  that made them. `updated` is when you made them.
- A data file is a list of rows, `[{"scenario": "ACC follow", "result": "pass", "minutes": 4.2}]`,
  or `{"columns": [...], "rows": [[...]]}`. Keep each value's type: numbers as numbers.
- A figure is a number the page shows on its own (a total, a rate, a change). You work it out
  from the rows when you write the data, put the result in `value` and say how in `formula`.

Read the sources with the file tools (`read_xlsx`, `read_file`, a connector), and write the data
with `write_file`, or with `run_python_script` when the rows need to be computed or are many.
Every number on the page comes from the person's data: never make one up. If the data they named
is not there, ask.

## The page

Start the head with the marker, and ask for d3 if you draw charts:

    <meta name="coscribe" content="dashboard">
    <script data-coscribe-lib="d3"></script>

Before the page's own script runs, `window.coscribe` holds `datasets` (each with its fields and
`rows`), `figures`, and `error` when the data could not be read. Write placeholders and fill them
from it:

- a figure: `<span data-figure="pass_rate">—</span>`, its text set from
  `coscribe.figures.pass_rate.value`, formatted with `Intl.NumberFormat`;
- a chart or a table: a container with `data-source="runs"`, drawn from
  `coscribe.datasets.runs.rows`;
- the time the data was made, from `updated`, in a quiet line under the title.

Draw charts with d3 as SVG: a `viewBox` and `width: 100%` so they fit their card, scales and axes
from d3, a few colours from CSS variables, a `<title>` on each mark for its value. Pick the chart
from the question: a line for change over time, bars to compare, a stacked bar for parts of a
whole (a pie only for two to five parts).

Layout: a title and one line on what the page shows; a row of figure cards; charts; then the
detail table with the rows behind them. Filters (a select, a few buttons) re-draw from the rows
in the page's own script. Style with CSS variables on `:root`, redefined in
`@media (prefers-color-scheme: dark)`; system fonts with a CJK fallback
(`system-ui, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif`); usable at 360 px wide.
When `error` is set or a dataset has no rows, say so in the card instead of drawing an empty chart.

## Refreshing

To refresh, read the sources again and write the data files and `datasets.json` again, with new
`updated` times. Leave the page as it is unless the person asked for a change to it.

## Before you say it is done

Check that every `data-figure` and `data-source` names an entry of `datasets.json`, that no
figure is typed into the page, and that nothing loads from the network. Say the page's file
name, what it shows and where its data came from, in a few lines.
