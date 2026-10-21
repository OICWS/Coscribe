# Docs editor: a picture's size and description (shipped)

Why: a picture could be shown and added but not sized, so a large one filled the page, and it carried no
description for people who cannot see it.

## Shipped
- Selecting a picture shows a bar over it: 25%, 50%, 75% and 100% of the text width (six inches), and a
  field for its description. Both are written to the file on the next save: the picture's extent in the
  paragraph (proportions kept, the shape's own size too) and the description of the drawing.
- Offered for a paragraph with exactly one picture, which is every picture added from the editor. A
  paragraph with several pictures, or a legacy picture, is shown and kept but not sized.
- The editor draws the picture at the chosen width, and the description is its alt text there.
- The server reads and checks the same two values (a width of 5 to 100 percent, a description of at most
  500 characters) and leaves the rest of the paragraph alone.
- Tests: writer (resized, described, nothing else rewritten, values out of range refused), vitest (both
  ways) and a Playwright spec (select, 50%, description, checked in the file).

## Not verified
- Percent steps only: a free drag handle and an exact size are not offered.
- How Word draws a picture sized this way, and a floating or cropped picture (resized by the same extent).
- The packaged app on Windows.

## Follow-ups
- Undo across coscribe's turns, version history: in `docs/plan.md`.
