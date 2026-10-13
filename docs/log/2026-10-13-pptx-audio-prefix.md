# add_pptx_audio declares its p14 prefix; the audio goldens land (shipped)

Why: The audio goldens were left out of the pptx golden work (#89) because the same call wrote different bytes depending on the process: `add_pptx_audio` built its `p14:media` element without declaring a prefix, so lxml named it `ns<N>`, N depending on what the process had done before (`ns6` in a local run, `ns1` in CI's full suite). The maintainer chose to fix it in the product code (#105).

## Shipped
- `src/coscribe/tools/presentations.py`: the `p:ext` element that wraps the media element is created with `nsmap={"p14": _P14_NS}`, one line changed. The slide XML now reads `<p:ext ... xmlns:p14=...><p14:media .../>` in every process.
- `test_add_pptx_audio_declares_the_p14_prefix` (in `test_presentations_tool.py`) parses the written slide and checks that `p14:media` keeps its prefix and no element is named `ns<N>`. It failed on `main` before the change.
- Three audio decks with goldens, 30 in all: `audio_auto_visible` (1.5 s delay, visible icon), `audio_on_click`, and `audio_after_animation` (a hidden track on a slide that already has an animation, sharing one timing tree). The audio source is a committed 0.1 s silent WAV.
- Verified in one process: the whole test suite ran in a single pytest process, the way CI runs it, which is how the problem first showed up.

## Not verified
- Windows: only Linux was run. The nightly Windows job will show it.
- Real PowerPoint playback of the audio: the goldens pin the XML only.

## Follow-ups
- A search of `presentations.py` for undeclared prefixes found one more: `set_pptx_transition` sets `mc:Ignorable` on the slide root with no `mc` prefix declared, so it is written as `ns0` (pinned in the `transition_and_animation` golden). It is stable today; left as is and filed as #174.
