# pptx goldens cover charts (shipped)

Why: Chart decks were left out of part 2a (#91). The Excel workbook python-pptx embeds with each chart writes the time of the build into its own `docProps/core.xml`, so the deck differed on almost every run. The maintainer chose to fix this in the canonicaliser, not in the product (issue #93).

## Shipped
- `office-agent/tests/pptx_canonical.py`: a member under `ppt/embeddings/` that is an Office package (`.xlsx`, `.docx`, `.pptx`) is opened. Its members are canonicalised in name order by the same rules as the deck's own, in place of a hash. That means sorted attributes, and only `dcterms:created` and `dcterms:modified` blanked in its `docProps/core.xml`. Nothing else is normalised. A golden now shows the chart's data twice, in the chart XML and in the workbook's sheet.
- Four chart decks with goldens: bar, line and pie with one series, and a bar chart with three series. That makes 13 decks in total. The existing goldens are unchanged.
- Stability probe: I built all decks twice, in separate processes (`PYTHONHASHSEED` 5 and 91, three seconds apart, different folders). Every canonical part was identical. Inside each embedded workbook, only `docProps/core.xml` differed in bytes, and nothing in it but the two timestamps.
- Changing one number in the chart data (120 to 125) fails the deck's test. The diff shows the value in the chart's `<c:v>` cells and in the sheet's `<v>` cell.

## Not verified
- On Windows: the nightly Windows job runs these tests.

## Follow-ups
- More decks for #89: icons, stat slides and the other layout directives, then templates, then audio and CJK text.
