# pptx goldens cover icons, shapes and every layout directive (shipped)

Why: Part 2 of the pptx goldens (issue #89) needs every layout directive and every tool group covered before `tools/presentations.py` is split. This is the group of icons, stat slides and the other layout directives.

## Shipped
- Five decks with goldens, 18 in all:
  - `icon_list`: `layout: icon-list`, with an accent colour, glyphs and a plain item.
  - `stat_callout`: `layout: stat-callout`.
  - `svg`: `layout: svg`, with a background rect, a circle, a rounded rect, a path and text.
  - `icon`: `add_pptx_icon`.
  - `shapes`: three `add_pptx_shape` types with text, fill and line.
- With `two-column` from part 1, all four layout directives (`_LAYOUT_IDS`) now have a golden.
- Stability probe: I built all 18 decks twice, in separate processes (`PYTHONHASHSEED` 11 and 4242, three seconds apart, different folders). Every canonical part was identical. The existing goldens are unchanged.
- Changing one stat (98% to 97%) fails the `stat_callout` test, with the `<a:t>` lines in the diff.

## Not verified
- Whether the `icon` golden holds on Windows. `add_pptx_icon` recolours a bundled PNG and re-encodes it with Pillow at runtime. That is product code, so the bytes come from the machine's Pillow and zlib, and a fixture can't stand in as it did for the test images in #91. The golden records the PNG's hash, so another encoder fails the test with no product change. The nightly Windows job will show it.

## Follow-ups
- If the Windows run shows a different icon hash: the canonicaliser could hash an image's decoded pixels instead of its file bytes. That is for the maintainer to decide, since it changes what counts as "the same image" for every golden.
- More decks: templates and SmartArt edits, then audio and CJK text.
