# pptx goldens cover audio and CJK text (shipped)

Why: The last group of part 2 of the pptx goldens (issue #89): `add_pptx_audio` and Chinese text, before `tools/presentations.py` is split.

## Shipped
- Six decks with goldens:
  - `audio_auto_visible`: `add_pptx_audio` with a delayed auto-start and a visible speaker icon.
  - `audio_on_click`: `trigger="on-click"`.
  - `audio_after_animation`: a hidden audio track added to a slide that already has an animation, so both share one timing tree.
  - `cjk_bullets`: Chinese bullets, which get the Microsoft YaHei East-Asian font fix.
  - `cjk_table_and_chart`: a Chinese table and a chart with Chinese categories (the embedded workbook is canonicalised).
  - `cjk_template_fill`: `fill_pptx_template` with Chinese content.
- The audio source is a committed 0.1 s silent WAV (`assets/narration.wav`), like the test images, so no encoder runs at test time. The speaker poster image is a constant in the product code.
- Stability probe: all six built twice in separate processes (`PYTHONHASHSEED` 11 and 4242, three seconds apart, different folders). Every canonical deck was identical.

## Not verified
- Windows: only Linux was run. The nightly Windows job will show it.
- Real PowerPoint playback of the audio: the goldens pin the XML, not how an application plays it.

## Follow-ups
- `cjk_template_fill` and `cjk_table_and_chart` are large (about 96 KB and 49 KB) because they carry a master and layouts that differ from `_shared.txt`; see the proposal in #122 for a second shared golden.
- With this group all tool groups named in #89 have a golden (30 decks).
