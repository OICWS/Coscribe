# A build names what a page uses that the design system does not have (shipped)

Why: a deck can begin from a design system of the person's library (decision 0020), but nothing
told coscribe, or the person, when a page then used another color or font.

## Shipped
- `engine/design_check.py`: `off_system(system, pages)` lists, per page, the colors (with the
  nearest palette color), fonts and `data-text-style` ids that are not in the system. White and
  black are always allowed; a color within 16 RGB steps of a palette color counts as that color;
  the generic font families are allowed; with no fonts or no palette in the system that check is
  skipped. `library_system(folder)` reads `design-system.json` and returns it only when it names a
  `source`, so a deck's own system (made from its pages) is never checked.
- `build_deck` adds the findings to each page's warnings, which the build tool already hands back
  to the model. They are warnings, not errors: the system guides, it does not forbid.
- `design_system.py` takes its patterns and file name from `design_check.py` (the leaf module, to
  keep the import order free of a cycle through `view` and `build`).
- `tests/test_deck_design_check.py`.

## Not verified
- With a real model: whether it repairs the warnings or leaves a stray with a reason.
- The thresholds (16 steps, white and black always) were chosen, not measured on real decks.

## Follow-ups
- Show the findings to the person in the Slides panel (today only the model sees them).
- Assets, the "describe it" conversation, extraction from a .pptx, the Design System kind in
  Artifacts (docs/plan.md).
