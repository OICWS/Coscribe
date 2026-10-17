# Cards for the four Office format components (partly shipped)

Why: issue #348 item 1. A session changing Word, Excel, PowerPoint or PDF should read a card of
that format, not the 25k-line `tools` card.

## Shipped
- `AGENTS.md` (and `CLAUDE.md` importing it) in `tools/office/{docx,xlsx,pdf,pptx}`; each is a
  component in `components.toml`.
- `tests/test_module_cards.py` reads sub-package cards too. For a sub-component, "Depends on"
  names siblings inside `tools.office` (for example `coscribe.tools.office.pdf` for pptx), other
  modules of `coscribe.tools`, and other top-level packages. Both checks were shown to fail by
  renaming a dependency and by removing an exported name from a card.
- The `tools` card points to the format cards.

## Not verified
- The "Verify by hand" lines are what to check on a real Windows machine; none was run.

## Follow-ups
- Cut `tools.exec`, `tools.web` and the bookkeeping tools into components (#348 item 1).
