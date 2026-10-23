# Design systems appear on the Artifacts page as their own kind (shipped)

Why: design systems lived only in Settings, so the page where the person looks for what coscribe
made did not show them. Issue: #569.

## Shipped
- `GET /api/design-systems` lists each system's first eight colors (`palette`) for a card to draw
  (`tools/design_systems.py`).
- `lib/artifacts.ts`: `PageKind` (the file kinds and `design-system`), `SystemItem`, `PageItem`;
  the listing, filters, counts, day groups and the pins work over `PageItem`.
  `lib/designSystemItems.ts` reads the library as items and renames, copies and deletes a system
  through the existing routes. The page reads the library beside the files, and one that cannot be
  read leaves the files showing.
- The card draws the palette as swatches; the list row and the type filter carry the kind; the
  "Make something new" tile for a design system opens Settings on its new-system form; a card opens
  Settings on that system's editor (`DesignSystemsTab` takes `start`: "new" or a system's id).
- `DesignSystemMenu`: Rename, Duplicate (a copy named "<name> copy"), Pin, Delete, which says the
  decks already made from it keep their own copy. No Open in program, Show in folder or Copy path.
  `RenameDialog` moved to its own file for both menus.
- Tests: `lib/artifacts.test.ts`, two cases in `tests/e2e/artifacts.spec.ts`, a server test.
- Ratchet accepted growth in `App.tsx`.

## Not verified
- Windows and the desktop app.
- A library of many systems: the page lists them all.
- A duplicate is made in two steps (create, then save the original's fields into the copy), so a
  failure between them leaves an untouched new system under "<name> copy".

## Follow-ups
- The "describe it" conversation, assets, extraction from a .pptx (docs/plan.md).
