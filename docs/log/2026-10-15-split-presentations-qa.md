# The deck checks move out of tools/presentations.py (shipped)

Why: #232 item 5, part 2 (part 1 moved transitions, animation and audio).

## Shipped
- A pure move: 383 lines leave `tools/presentations.py` (6,109 to 5,726) for `tools/office/pptx/qa.py` (404 lines): the overflow check on the LibreOffice render, leftover placeholder text, overlapping text boxes, slides without a visual element, sparse or cramped layouts and low contrast. The module needs only the standard library and python-pptx objects it is given.
- The names the toolkit and the tests use are public (`check_overflow`, `check_low_contrast`, ...); `OVERFLOW_TOLERANCE_PT` moved with them. `_render_to_pdf` stays in `presentations.py` because `tests/conftest.py` patches it there.
- Tests import the checks from `qa`; their bodies are unchanged. `quality/baseline.json`: `presentations.py` 6,109 to 5,726. `docs/plan.md` item 0b lists what is still to move.

## Not verified
- PowerPoint itself: the code is the same, checked by the existing LibreOffice-render and template tests.

## Follow-ups
- Part 3 and 4: theme and template helpers; SmartArt, shape description and effects (#232, item 5).
