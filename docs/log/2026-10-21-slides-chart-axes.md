# Slides: chart axis titles, range and number format (shipped)

Why: the chart panel had no axis options although the engine writes them (open item since the
chart panel).

## Shipped
- The chart panel has an Axes section: a title for each axis, the value axis's minimum and maximum
  (blank is automatic) and its number format (automatic, 1,234, 1,234.5, 12%, 12.3%).
- The panel's picture of a chart draws them too (titles, the fixed range, the format on the tick
  labels), so a control never changes only the .pptx.
- The sections guide tells the model to keep these keys when it edits a chart.

## Not verified
- How PowerPoint places the axis titles; the panel's picture is an approximation of it.
- Not run in a live server or the app.
