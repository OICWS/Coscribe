# A file can be dropped anywhere on the window (shipped)

Why: a file dragged onto the page only worked over the message box; anywhere else nothing showed,
and in the desktop app the file could open in place of the page.

## Shipped
- `lib/useWindowFileDrop.ts`: while a file is dragged over the window the whole window gets an
  accent frame with "Drop files to attach", and a drop that no other target took attaches the
  files like the file picker does. A drag with no file (a thread, a slide) is left alone, and
  so is a drop while a dialog is open.
- `Composer` uses it in place of its own drop zone, so the frame is the same wherever the file
  is dropped.
- Tests: `tests/e2e/composer-drop-paste.spec.ts` (the frame, a drop beside the message box, a
  drag without a file).

## Not verified
- The desktop app on Windows, with a file dragged from Explorer (the specs dispatch the drag
  events); the look of the frame was not seen.
- Pages without a message box (Artifacts, Scheduled) take no drop.
