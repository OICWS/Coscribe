# The Slides panel has a chart panel (shipped)

Why: a selected chart showed no properties, though the engine already writes its title, legend,
data labels, type, stacking and series colours into the native PowerPoint chart.

## Shipped
- `lib/slideChart.ts` reads and changes the keys of an `<x-chart>`'s JSON; the panel
  (`SlideChartProperties.tsx`) offers type (column, bar, line, area), stacked (column and bar),
  title, legend, data labels and one colour per series (the deck's palette first).
- Only what the engine honours is offered: `tests/test_deck_chart_keys.py` builds a deck with each
  key and checks the chart XML has the legend, labels, title, stacking, colours and chart type, so a
  control never changes only the picture of the chart.
- A chart of another type (pie, scatter, ...) shows the title, legend, labels and colours but no
  type menu: swapping it needs one series or a different data shape.
- Tests: `lib/slideChart.test.ts` (jsdom).

## Not verified
- Opened in Chromium against a live server (type, legend, labels, title reached the saved page and
  the stage), not in PowerPoint. The stage's picture of a chart does not draw data labels, so a
  labels toggle shows only in the exported deck.

## Follow-ups
- Axis titles, axis range and number format are honoured by the engine and not offered yet.
