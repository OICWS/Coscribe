# The design-system library: the store and its routes (partly shipped)

Why: step 2 of the Artifacts plan (decision 0020, accepted): a person keeps design systems in the app and a deck gets a copy. This is the first part; nothing in the UI uses it yet.

## Shipped
- `tools/design_systems.py`: `DesignSystemStore` keeps one folder per system under the state directory (`design_systems/<id>/system.json`, written atomically under the file lock). A system holds a name, an overview, colors (name, `#RRGGBB`, note), typography (fonts and text styles with size, weight, line height, letter spacing), spacing and corner radius. A new system starts with four colors and the six text styles a deck needs. A save is checked (`DesignSystemError`: an unreadable color, a wrong type, a duplicate style id, a size limit) and changes nothing when refused. An id is ten hex characters and never names a path outside the library.
- `GET/POST /api/design-systems` and `GET/PUT/DELETE /api/design-systems/{id}` (`web/routes/settings/design_systems.py`); a refused save answers 400 with the reason.
- Tests: `tests/test_design_systems.py` (store) and `tests/web/test_design_systems.py` (routes); route and OpenAPI snapshots updated; the two GET routes are in the audited read-only list.

## Not verified
- Nothing in the app reads or shows these routes yet.

## Follow-ups
- Settings > Design systems (list, "New design system", a detail page per section), then assets (logos, icons), the "describe it" conversation, extraction from a .pptx, the Design System kind in Artifacts, and the Slides chip's choice (`docs/plan.md`).
