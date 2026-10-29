# A Doc's chart reads as a chart; the ask box keeps its suggestions on one line (shipped)

Why: in the maintainer's Doc a line chart sat on an axis from 0, so a change from 2,480 to 2,710
read as a flat line (Word's export fitted the axis and showed it). Its source, a table of numbers
in a code box, showed under it at all times and read as if the chart had failed. The ask box
wrapped its three suggestions onto two lines in a wide panel.

## Shipped
- Chart axes take round steps (1, 2, 2.5, 5 × 10ⁿ). A line chart's axis fits its values; bars
  still stand on zero.
- A chart's source is hidden until the caret is in it; a click on the chart puts it there.
- The ask box: an "@Coscribe" tag before the input, a send button, and the suggestions on one line
  (wider box; they wrap only when the panel is narrow).
- e2e: two more cases in `doc-editor.spec.ts`; a unit test of the axis.

## Not verified
- The desktop app. Moving into a hidden chart source with the arrow keys works (the caret reveals
  it) but wasn't tried by hand.
