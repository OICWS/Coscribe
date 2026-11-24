# Dialogs sit in the middle of the desktop window (shipped)

Why: in the desktop app the Settings dialog looked low. It kept a margin only below the title bar
row (56px above it, 16px below it), but that row is dimmed with the rest of the window, so it reads
as empty space.

## Shipped
- `lib/titleBar.ts` has one inset for every full-window dialog layer, `DIALOG_INSET_CLASS`: in the
  desktop app the same 3.5rem above and below (the 2.5rem row plus 1rem), 1.5rem at the sides; in
  a browser 1.5rem all round. `DIALOG_BACKDROP_CLASS` is built on it.
- Settings and the other full-window dialogs (schedule, failed turn, folder browser, shortcuts,
  confirm, rename, link, run inputs, toolbar, add connector, first workspace, attachment, image
  and text viewers) use it, and the tall ones cap their height at `100%` of it instead of `vh`, so
  none reaches under the window buttons. At 1280x860 Settings now has 56px above and below it.

## Not verified
- On a real Windows window: checked in Chromium with the desktop bridge stubbed.
