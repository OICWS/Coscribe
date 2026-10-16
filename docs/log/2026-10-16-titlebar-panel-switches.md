# Panel switches in the desktop title bar, one scrollbar style (shipped)

Why: the maintainer wants the panel switches on one line with Settings and
the window buttons, as a first step to opening several panels at once, and
every scrollbar drawn the same way.

## Shipped
- `App.tsx`: in the desktop shell, the Task details, Browser and Background
  tasks switches sit in the title bar left of Settings, after a thin divider,
  with 12px more between Settings and the OS minimize button. In a browser tab
  they stay at the right end of the conversation's header. An open panel's
  switch is drawn in the accent's soft blue, not the hover grey.
- `index.css`: scrollbars are 12px with a 6px rounded thumb, light grey at
  rest and dark grey under the pointer, and one small arrow at each end, in
  both themes.

## Not verified
- Checked in Chromium with the desktop title bar simulated (as
  `titlebar.spec.ts` does); not in the Electron app on Windows, where the
  OS window buttons are drawn over the row's right end.

## Follow-ups
- Several panels open at once, arranged by dragging (issue to follow).
