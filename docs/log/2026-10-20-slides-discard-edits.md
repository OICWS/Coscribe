# Slides: discard my edits, Ctrl+wheel zoom, a format bar that stays on the stage (shipped)

Why: the maintainer's testing of the packaged app.

## Shipped
- "Discard my edits" in the presentation's menu takes back every change the user made since
  coscribe's last version (after a confirmation); Redo brings them back. The history already
  records who made each state, so it walks back over the states made by the user
  (`step_history(..., discard=True)`). The Undo and Redo buttons added to the toolbar are gone;
  Ctrl+Z and the zoom menu's entries stay.
- Ctrl and the wheel zoom the stage by the zoom menu's steps.
- The format bar goes under the selection when there is no room above it and is kept inside the
  stage's width, so selecting a box at an edge no longer makes the stage scroll.

## Not verified
- Not run in a live server or the app.
