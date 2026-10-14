# PowerPoint part 2: a new deck on the user's own template is built from pages (shipped)

Why: a deck on the user's template still went through `extract_pptx_template` and
`fill_pptx_template` (title and bullets in the template's slides) and scored lowest of all tasks
(task 06, design 2.6 to 2.9). Decision 0010 lists the user's own template built from pages for
part 2.

## Shipped
- `engine/template.py`: with `template`, the slides are made from the template's own file, so
  its master, layouts, theme colours and fonts carry over; its example slides are left out. A
  page's root takes `data-template-slide="N"` to start from example slide N's background and
  decoration (bands, panels, pictures, copied with their images), since many templates draw
  their design there rather than on the master; or `data-layout` names a layout. Every page's
  viewBox must be the template's slide size. A `.potx` is read as the `.pptx` it would make.
- A copied example keeps every relationship it refers to: pictures (the background's too) are
  added to the slide, a web link keeps its target. A shape referring to anything else (a chart,
  SmartArt, media, a link to another slide) is left out with a warning naming it, so the slide
  never points at a part it does not have. Copied shapes get ids above the page's own, so no two
  shapes on a slide share one.
- `describe`: the template's viewBox, background, theme colours and fonts, layouts, and each
  example slide's layout, background and decoration (kind, box in px, fill or gradient stops).
  `build_pptx_from_pages(template=...)` returns it while the pages folder is still empty, so the
  model designs from it in one call, and builds on the template afterwards.
- "PPTX Pages": a section on the user's template (describe first, the template's colours and
  fonts, start each page from a fitting example slide, draw no background).
- `coordinator.py` and the new-deck paragraph: a new deck on the user's template, or in the
  design of a reference deck, is built from pages with `template`, not with
  `extract_pptx_template` and `fill_pptx_template`. The system prompt is 848 characters
  shorter.
- `tests/test_deck_engine_template.py` (10 tests): the description, a page starting from an
  example slide (decoration, layout, picture and its image, the example slides gone), layouts
  by name and a wrong name, wrong references, a .potx described and built, the tool describing then building, an example
  slide with a picture background, a web link and a chart (every relationship resolves, the chart
  is left out with a warning), copied shapes' ids unique.

## Checked (2026-10-14, off-peak)
Task 06 (a quarterly report on the user's template), `deepseek-flash` at effort low, 3 judge
rounds; before is the same task on `extract_pptx_template` / `fill_pptx_template` in the
measurement and on the cut prompt.

| | Design | Content | Coherence | Facts | Tool calls | Cost |
|---|---|---|---|---|---|---|
| Pages on the template | 3.90 | 4.27 | 4.27 | 12/12 | 33 | 0.045 |
| Before (two runs) | 2.63 / 2.87 | 3.07 / 3.30 | 3.27 / 3.47 | 12/12 | 18 / 33 | 0.015 / 0.018 |

- The five pages started from the template's cover, content and closing slides
  (`data-template-slide` 1, 2, 2, 3, 4) and kept its navy gradient panels and bottom band; the
  content used the template's colours. About one point more on every score.
- It costs 2.5 times as much (about 0.3 yuan a deck): whole pages are written, and the deck was
  built five times. The cover title broke over three lines.

## Not verified
- Windows and PowerPoint; templates whose master holds pictures or SmartArt.
