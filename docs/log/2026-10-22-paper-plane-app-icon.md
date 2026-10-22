# New app icon: a paper plane (shipped)

Why: the old icon was a white tile with "oa" on blue, left over from the office-agent name. The maintainer asked for an icon without a background tile and picked a paper plane from ten sketches.

## Shipped
- `office-agent-desktop/icons/icon.svg` is the new source: three gradient facets (teal to blue, pink to violet, deep indigo), no tile, no shadow.
- `icon.png`, `32x32.png`, `64x64.png`, `128x128.png`, `128x128@2x.png`, `icon.ico` (16 to 256 px) and `icon.icns` are re-rendered from it with a transparent background. The tray and the packaged exe use these files.

## Not verified
- Not run on Windows: how the icon looks on the taskbar, tray and installer is unchecked. Checked only as PNG renders in headless Chromium.
- `icon.icns` was written with Pillow and not opened on macOS (macOS is not developed).

## Follow-ups
- The web UI has no favicon; adding one from `icon.svg` is a separate change.
