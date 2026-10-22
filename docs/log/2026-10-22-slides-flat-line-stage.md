# A flat line stays on the Slides stage

Why: a footer rule drawn as a `<line>` showed in the slide's picture and in the presentation, but in the editor it flashed and went once the stage drew the slide itself.

## Shipped
- `sectionDom.ts`: the drawing of a line is never zero in either side. A horizontal or vertical line has a box with one side 0, and the browser paints no svg of zero size even with `overflow: visible`.
- A unit test draws the footer rule of a converted page and checks the svg is 1 px tall with the line at its top.

## Not verified
- Not run on Windows or in the desktop shell; checked in headless Chromium against the maintainer's cover slide (the rule is back at its row, below the grid line).
