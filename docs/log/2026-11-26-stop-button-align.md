# The composer's Send/Stop button sits level with the text (shipped)

Why: the Stop button looked a little too high in the message box.

## Shipped
- `frontend/src/components/Composer.tsx`: the Send/Stop button was anchored `bottom-3` (12px), the
  same as the box's padding, but it is 28px tall against a 21.6px text line, so its middle sat
  3.2px above the line's middle. It now sits 8.8px from the bottom (`besideLastLine`), measured
  in Chromium: the button, its icon and the one-line text all centre at the same y. With several
  lines it stays beside the last one.

## Not verified
- The Windows desktop app; measured in Chromium on Linux.
