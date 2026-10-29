# The Slides panel shows the pages written so far while a deck is being built (shipped)

Why: while coscribe wrote a deck's SVG pages the panel only said "Coscribe is working on X.pptx…" on
grey, for minutes, and the maintainer saw nothing of the build.

## Shipped
- `lib/draftPages.ts`: the `.svg` files the run has written (successful writes, the folder written to
  last, in file-name order, which is the slide order). `ViewerPanel` gives them to the panel of a deck
  through a context while a turn runs; with none it keeps the old line.
- The panel of a deck that is not built yet draws them page by page ("N pages so far"), each fetched
  again when it is written again.
- `slides-drafts.spec.ts` (and a unit test): three pages and a placeholder deck; the panel shows
  "3 pages so far" and the images.

## Not done
- A deck that is already built and is being rebuilt keeps showing the old slides until the build ends.
- Pages that use an image by relative path show without it (the page is drawn as a picture).
