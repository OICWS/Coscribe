# Slides: thumbnail icon, new objects, notices and undo buttons (shipped)

Why: found by the maintainer testing the packaged app.

## Shipped
- The "show thumbnails" icon is drawn as large as the speaker-notes icon next to it.
- A new object starts a step down and right of where an element already starts, so a second
  "Text" no longer lands exactly on the first and trips the overlap check.
- A problem the build reports after an edit is a card floating over the stage instead of a row
  that pushes the slide down and back up.
- Undo and Redo are buttons in the stage's toolbar (they were only in the zoom menu).
- Ctrl+Z after moving or resizing an object took effect only after a click elsewhere: the redraw
  after the change dropped focus, so the key never reached the panel. The editor takes focus back
  when a drag starts and ends.

## Not verified
- Not run in a live server or the app. The focus cause is read from the code (the maintainer's
  description: a move, then Ctrl+Z does nothing until a click), not reproduced.

## Follow-ups
- Selecting a drawing from an SVG slide shows the slide's settings; it should say what it is.
