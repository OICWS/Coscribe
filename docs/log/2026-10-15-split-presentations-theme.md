# The deck theme code moves out of tools/presentations.py (shipped)

Why: #232 item 5, part 3.

## Shipped
- A pure move: 247 lines leave `tools/presentations.py` (5,726 to 5,479) for `tools/office/pptx/theme.py` (272 lines): the `theme=` token parser, the colour-scheme slots and tags, reading and writing scheme colours, the East-Asian font fallback and `apply_theme`.
- The names the toolkit uses are public; `theme.py` imports the schema validator from `tools/_ooxml_validate.py` and nothing from the toolkit. `quality/baseline.json`: `presentations.py` 5,726 to 5,479. `docs/plan.md` item 0b lists what is still to move.

## Not verified
- PowerPoint itself: the code is the same, checked by the existing theme tests and the LibreOffice render tests.

## Follow-ups
- Part 4: SmartArt, shape description and effects, template slide copying (#232, item 5).
