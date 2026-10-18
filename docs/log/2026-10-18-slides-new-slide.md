# Slides editing, part 6b: New slide, and the thumbnails' Duplicate, Delete and drag

Why: the "+" and its New slide dialog from the maintainer's mockups, and managing slides from
the thumbnail strip (design §7, issue #431).

## Shipped
- "+" at the left of the bar under the slide opens New slide: the ten layouts of the mockup
  (Blank, Title, Section, Title + body, Bullets, Two columns, Table, Quote, Image + caption,
  Closing), each drawn in the current slide's background, text colour, accent and font
  (`lib/slideLayouts.ts`). A pick adds that slide after the current one and shows it.
- A right-click on a thumbnail: New slide after this, Duplicate, Delete (not the last slide).
- Dragging a thumbnail onto another moves the slide there.
- The slide drawn in the page draws a shape or a table itself until the server's picture of it
  arrives, which is what the dialog's previews show.

## Checked
- In Chromium against a live server with the Q3 deck: the dialog opened with the ten layouts in
  the deck's look; Bullets added after slide 2; that slide duplicated from its menu; the copy
  dragged to the front. The page files and thumbnails followed each change.

## Not verified
- Dragging thumbnails with a touchpad on Windows.
