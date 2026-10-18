# Slides editing, part 3: select, move, resize, nudge, delete

Why: the first editing the design lists (§3) on the slide itself, per the maintainer's mockups
(issue #431).

## Shipped
- A click on the slide in Slide view starts editing it: the slide is read as parts
  (`GET .../slides/{index}/parts`) and drawn as the page's own elements in a shadow root:
  - text in its own tags, laid out as the compiler lays it out (default sizes per tag, padding,
    vertical alignment, lists);
  - everything else as the server's picture of that element alone;
  - a style value that calls a CSS function (`url()`) is never applied.
- The editor: a click selects the topmost element, a drag moves it, eight handles resize it
  (Shift keeps proportions from a corner), arrows nudge 1 px (Shift: 10 px), Delete removes,
  Escape lets go and then leaves editing.
- Every change is saved at once (`PUT .../source`), in order, each save naming the version the
  last left. A resized picture is read again so the server draws it at its new size; the deck's
  thumbnails redraw after each save. A slide changed meanwhile is read again; the build's errors
  on the slide (text that no longer fits) show under the header.
- `lib/slideSource.ts` (the section source as the editor changes it) with tests;
  `lib/slideEditing.ts` (the two calls).

## Checked
- In Chromium against a live server with the six-slide Q3 deck:
  - slide 2's title selected, dragged and saved: the page became `02-at-a-glance.html` and the
    thumbnail redrew;
  - slide 3's native bar chart resized from a corner: redrawn at its new size;
  - the footer nudged with the arrows and deleted.

## Not verified
- Editing on Windows with a mouse and touchpad, and in the Electron app.
