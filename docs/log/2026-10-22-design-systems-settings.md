# Settings > Design systems: the library's list and form (partly shipped)

Why: step 2 of the Artifacts plan (decision 0020). The store and routes were in the pull request before this one; this is where a person makes and edits a design system.

## Shipped
- A **Design systems** category under Customize in Settings: the list (name, last change, Edit, Delete with a confirmation), **New design system** (a name, then the form), and a page per system with its sections on the left: Overview, Colors, Typography, Spacing, Corner radius. Save is enabled only for a change; a refused save shows the server's reason and keeps what was typed; Back asks before dropping unsaved changes.
- `sendForResult` shows FastAPI's `detail` as the reason, as it did for `error`.
- `tests/e2e/design-systems.spec.ts` (in the nightly list): make a system, edit and save it, a bad color is refused, see it in the list, delete it.

## Not verified
- Windows and the desktop app.
- Fonts are typed one per line, not picked from the fonts installed on the machine.

## Follow-ups
- Assets (logos and icons with a note on when to use each), "Used by" in the list, the "describe it" conversation, extraction from a .pptx, the Design System kind in Artifacts, the Slides chip's choice (`docs/plan.md`).
