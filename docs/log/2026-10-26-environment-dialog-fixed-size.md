# Edit environment dialog keeps one size on every page (shipped)

Why: moving between Folders, Network, Scripts, Secrets and Environment variables resized the dialog
each time, so the window jumped on every visit.

## Shipped
- `EnvironmentDialog.tsx`: the dialog has a height floor as tall as its tallest page (Network, 43rem),
  capped to the viewport. A long list (many folders) grows it up to the viewport, then the body scrolls.
- `rail-dialog.spec.ts`: the dialog's height is the same on the main page and every sub-page.
- Measured at 1280x800: main, Folders, Network, Scripts, Secrets and Environment variables all 688px
  (before: 640, 512, 680, 512, 512, 512).

## Not verified
- Windows and the desktop app; a very long Folders list (the existing body scroll is unchanged).

## Follow-ups
- None.
