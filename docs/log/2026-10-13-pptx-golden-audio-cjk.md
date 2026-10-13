# pptx goldens cover Chinese text; the audio group is not stable (shipped)

Why: The last group of part 2 of the pptx goldens (issue #89): `add_pptx_audio` and Chinese text, before `tools/presentations.py` is split.

## Shipped
- Three decks with goldens, 21 in all:
  - `cjk_bullets`: Chinese bullets, which get the Microsoft YaHei East-Asian font fix.
  - `cjk_table_and_chart`: a Chinese table and a chart with Chinese categories (the embedded workbook is canonicalised).
  - `cjk_template_fill`: `fill_pptx_template` with Chinese content.
- Stability probe: built twice in separate processes (`PYTHONHASHSEED` 11 and 4242, three seconds apart, different folders). Every canonical deck was identical.

## Finding: the audio group is not stable
- I built three audio decks (auto-start with delay, on-click, audio added after an animation). Standalone and in the golden test file they were identical run to run, so the first probe passed.
- In CI's full test run (1,911 tests in one process) the same decks differed from the committed goldens in one line: the prefix lxml gives the `p14:media` element. `add_pptx_audio` builds it without declaring a prefix, so lxml names it `ns<N>` (`ns6` locally, `ns1` in CI); N depends on what the process did before, not on the deck. The XML means the same either way.
- Per the issue, I did not change product code and did not hide it in the canonicaliser. The audio decks are left out.
- Options for the maintainer: (a) `add_pptx_audio` declares `p14` in `nsmap` (a one-line product change, and it makes the file match what PowerPoint writes); (b) the canonicaliser renames auto-generated `nsN` prefixes by order of appearance (a pptx-only step, but it changes what "the same" means).

## Not verified
- Windows: only Linux was run. The nightly Windows job will show it.

## Follow-ups
- Audio goldens (3 decks, drafted) after the maintainer picks (a) or (b).
- `cjk_template_fill` and `cjk_table_and_chart` are large (about 96 KB and 49 KB); see the proposal in #122 for a second shared golden.
