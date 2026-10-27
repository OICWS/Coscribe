# Doc artifact, step 4c: callouts and charts in the editor

Date: 2026-10-27
Area: frontend

A GitHub alert quote (`> [!NOTE]`, TIP, IMPORTANT, WARNING, CAUTION) is a coloured box of paragraphs in
the editor, with its kind in the box's corner; the "+" menu inserts one, and while the caret is in one a
"Callout" button in the toolbar changes its kind. A callout whose body is more than paragraphs (a list in
it) stays its own markdown, as raw html and unknown blocks do. A fenced `chart` block is drawn above its
source (bar, line or pie, `lib/docChart.ts`; every text in the SVG is escaped); the source stays what the
person edits, and a block that is not a chart says why in one line above it. The "+" menu inserts a chart
with sample data. Neither is written back unless the person changed it.

Not verified: a real Windows machine; the chart's look in dark mode and with many categories; the editor
still opens only through a local change to `isViewable` (step 5). Pictures are step 4d.
