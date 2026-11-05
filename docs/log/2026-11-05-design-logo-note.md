# look_at_page tells a Design canvas when no artboard places its design system's logo (shipped)

Why: a deck's build warns when no slide places the system's logo
(`docs/log/2026-11-05-unplaced-logo-warning.md`). A Design canvas has no build; `look_at_page` is
the step the Design skill asks for before a design is done, so the note goes there.

## Shipped
- **The note:** `look_at_page` on a canvas adds `design_system` to its result when the system
  the conversation started with has a logo and no artboard places it.
  - It checks every artboard, not only the ones drawn in that call, and counts the pictures
    inside parts.
  - A logo counts as placed by its file (sha256), as for a deck: a renamed copy counts, a redrawn
    one does not.
- **Shared code:**
  - The note's wording is `unplaced_logo` in `tools/design_systems.py`, which the deck's build now
    uses as well (`DesignSystemStore.unplaced_logo_for_thread` for a canvas).
  - `design_canvas.placed_pictures` finds a page's picture files by the same rule `with_pictures`
    uses to fill them in.
  - `build_page_tools` takes the conversation (`state_dir`, `thread_id`), as `build_http_tools`
    does.
- **The Design skill** says `look_at_page` reports a logo no artboard places.
- **Tests:**
  - `tests/test_design_canvas.py`: a page's pictures, its parts' included and nothing outside
    the folder.
  - `tests/test_page_tools.py`: the note appears when no artboard places the logo, and goes away
    once one places a renamed copy. There is no note when the conversation chose no system.

## Not verified
- `look_at_page` itself was not run here: this container's browser times out drawing a page, on
  `main` too. The note is tested apart from the screenshot.
- Not run with a real model.
- Checked on Linux only.
