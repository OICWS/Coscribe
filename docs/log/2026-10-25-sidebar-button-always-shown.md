# Edit toolbar no longer lets the sidebar button be hidden (shipped)

Why: unticking "Sidebar" in Edit toolbar removed the only button that brings a hidden sidebar back.

## Shipped
- `toolbarItems.ts`: `ALWAYS_PINNED` (the sidebar); `normalizePinned` keeps it even from an older stored choice that left it out.
- `ToolbarMenu.tsx`: the Edit toolbar dialog no longer lists always-pinned items.
- `App.tsx`: the sidebar toggle is always shown.

## Not verified
- Not run in the desktop shell; only unit tests and the frontend build.

## Follow-ups
- none
