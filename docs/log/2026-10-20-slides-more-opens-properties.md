# The format bar's ⋮ opens the properties panel (shipped)

Why: the mockups open the detailed settings beside the slide from the ⋮ of the floating bar; it
only showed Bring forward, Send backward, Duplicate and Delete, and the panel was reachable only
from the toolbar's button.

## Shipped
- ⋮ on the format bar shows the properties panel (the toolbar's button stays as the second way in).
- Those four actions moved into an Arrange section at the end of the panel, for any selected
  element; they are disabled as before (a container's children, nothing to swap with).
- `slides-panels.spec.ts` presses ⋮ and then Bring forward in the panel.

## Not verified
- Not run against a live server or the e2e spec; the frontend build, unit tests and lint pass.
