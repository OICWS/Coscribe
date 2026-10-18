# A deck's design system, read by the Slides panel (part 1 of the properties panel)

Why: the properties panel needs the deck's named text styles and palette (decision 0017).

## Shipped
- `tools/office/pptx/engine/design_system.py`: `design_system(deck)` reads `design-system.json`
  from the deck's pages folder. When there is none it is made from the pages (the colours they
  use, most used first, up to ten; their fonts; the six default styles Heading 1, Heading 3, Lead,
  Eyebrow, Body, Caption) and saved. A saved file is kept; a damaged one is replaced in memory by
  the default and not overwritten.
- `GET /api/threads/{id}/slides/design-system?path=`.
- A text element of a section may carry `data-text-style="<style id>"` (`section_format.py`).
- Tests: `tests/test_deck_design_system.py`.

## Not verified
- Nothing uses it yet; the panel that reads it is the next part.

## Follow-ups
- 0017 says a deck on a template takes its palette and fonts from the template's theme. A deck
  with sections is never built on a template (`build.py`), so that is not reachable yet; the
  default comes from the pages alone. Revisit when template decks can be edited.
