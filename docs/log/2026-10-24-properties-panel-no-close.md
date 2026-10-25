# The Slides properties panel has no close button of its own (shipped)

Why: the panel's top row held only an ×, which pushed the panel's content down, and the toolbar's
toggle beside the zoom, the ⋮ menu and a press on the empty stage all leave it already.

## Shipped
- `SlideProperties`: the row with the × is gone, so the panel starts at its first section.
  The toolbar's "Properties panel" toggle stays the way to hide it.
- `tests/e2e/slides-panels.spec.ts`: the panel has no close button.

## Not verified
- The look on Windows; the stacked layout (panel under the stage in a narrow window) was not seen.
