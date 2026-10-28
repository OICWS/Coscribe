# The scheduled task form lists existing environments (shipped)

Why: In the scheduled task form the environment picker showed only "New environment". Its menu opens upward, and the form's scrolling body and the rounded box around the picker clip anything that sticks out, so the list of existing environments was cut off.

## Shipped
- `EnvironmentPicker` with `forTask` renders its menu in a portal on `document.body`, fixed below the button, so no ancestor clips it. The conversation picker is unchanged.
- Click-outside now also treats the portaled menu as inside.

## Not verified
- Not run in a browser here; checked with `tsc -b` and prettier only.

## Follow-ups
- none
