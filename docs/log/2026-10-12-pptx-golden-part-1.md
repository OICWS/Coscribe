# Golden XML tests for pptx, part 1: the generated XML is stable (shipped)

Why: `tools/presentations.py` (about 7,000 lines) is to be split by pure moves, and a pure move must be shown to leave every deck byte-identical (assessment step 9, issue #86). That needs the XML to be the same from one run to the next.

## Shipped
- Finding: it is. Five decks (bullets, table, two-column, a transition plus an animation, a theme change) were built through the public tools twice, in separate processes with different `PYTHONHASHSEED` values and output paths. Every zip member was byte-identical. Only the zip itself differed: each member carries the time of the save. Shape ids, relationship ids and the member order did not change.
- `office-agent/tests/pptx_canonical.py`: reads members in name order, which drops the zip's timestamps, sorts attributes, indents XML and replaces each binary with its size and hash. It also blanks `dcterms:created` and `dcterms:modified` in `docProps/core.xml`. Those two did not vary in the probe (they are the python-pptx template's fixed 2013 values); they are blanked so that a later save-time stamp does not break every golden.
- `office-agent/tests/test_office_golden.py`: builds each deck and compares it with `office-agent/tests/golden/pptx/<deck>.txt`. `UPDATE_GOLDENS=1` rewrites them. A second test fails on a golden that no deck builds. The tests skip the LibreOffice QA pass, which only reads the deck, and take under a second.

## Not verified
- Stability on Windows and macOS: only Linux was checked (locally twice, and in CI). The nightly Windows job runs these tests and will show it.

## Follow-ups
- More decks (charts, images, icons, shapes, templates), then docx and xlsx goldens.
- Every deck's `docProps/core.xml` carries python-pptx's template metadata (`lastModifiedBy` "Steve Canny", description "generated using python-pptx", 2013 dates). That's a product question for its own issue, not a test change.
