# Slides: thumbnail icon, new objects, notices and undo buttons (shipped)

Why: found by the maintainer testing the packaged app.

## Shipped
- The "show thumbnails" icon is drawn as large as the speaker-notes icon next to it.
- A new object starts a step down and right of where an element already starts, so a second
  "Text" no longer lands exactly on the first and trips the overlap check.
- A problem the build reports after an edit is a card floating over the stage instead of a row
  that pushes the slide down and back up.
- Undo and Redo are buttons in the stage's toolbar (they were only in the zoom menu).

## Not verified
- Not run in a live server or the app. Ctrl+Z not taking effect, as the maintainer saw, is not
  reproduced; the shortcut is wired in `SlidesPanel.tsx` and ignored while an input has focus,
  where the browser's own undo runs instead. The buttons work whatever has focus.

## Follow-ups
- Selecting a drawing from an SVG slide shows the slide's settings; it should say what it is.
