# Deck engine, part 2a: the checks and the build from a folder of pages (shipped, no tool yet)

Why: decision 0010's engine needs to tell the model what is wrong with the pages it wrote (the
checker, with at most two repair rounds) and to keep a deck's page sources and its .pptx in step,
before any tool exposes it (issue #198, PR 1 of 4).

## Shipped
- `tools/office/pptx/engine/checker.py`: on the compiled deck, in the positions PowerPoint uses
  (the emitter has measured every line with its font's metrics):
  - errors: XML PowerPoint's schema rejects (it can mean a repair prompt; `xml:space` on a text run
    is not reported: PowerPoint accepts it, and the part 1 deck that opened cleanly on Windows has
    it); text past the page edge; text drawn over text; text that cannot be read (contrast under
    1.5:1);
  - warnings: faint text (under 3:1, worst four listed per page); numbers on a page that no
    source file has (page numbers and integers up to 31 skipped; axis ticks and computed figures
    are named as fine in the message).
  Contrast is measured against what is really behind the text: translucent fills blended over
  what is under them, gradients as the mean of their stops, nothing claimed over a picture.
  `source_text` reads .docx, .xlsx, .pptx, .pdf and plain text files.
- `tools/office/pptx/engine/build.py`: `build_deck(pages_dir, out, sources=...)` compiles every
  `*.svg` in the folder in file-name order (numbers compared as numbers), checks it and writes
  `build.json`: a hash per page and per slide (its XML, relationships and the bytes of what they
  point to). A rebuild is refused with `DeckChangedError` when the .pptx is not exactly what the
  pages last built (changed in PowerPoint or by an object tool, or another file at that path),
  unless `replace_changes`. The report lists the pages whose source changed since the last build.
- `compile_pages` takes `svg_dir`: an image is found relative to the pages' folder and must stay
  inside `resource_root` (the workspace).
- Thresholds set on the 130 pages deepseek-flash wrote in the research (10 conditions, two
  briefs), checked against their renders. First attempt: 985 contrast warnings, mostly blue text
  on a 12% blue tint read as solid blue; blending the alpha and moving the bar from WCAG's 4.5:1
  to 3:1 (4.5 flagged the grey captions of the decks the judges rated best) left 75 page-level
  warnings. Text-over-text: 42 errors at first, almost all a large number and its unit or label,
  whose frames overlap while their glyphs do not; with a glyph box (0.8 em above the baseline,
  0.15 below, the emitter's line-end headroom removed by alignment) and faint text excluded, 1 is
  left, a real defect. The errors left on the 130 pages: a cover whose dark band is 160 px tall
  under white text at y 328 (white on white, the `none` effort deck the report says breaks pages),
  a label drawn on its own bar (#2C5F8A on #3B76A6), and that one overlap. No slide of the 130
  breaks the schema once `xml:space` is set aside (83 had only that).
- `tests/test_deck_engine_checks.py` (20 tests): each check flags its defect and passes the
  look-alike (number with unit, tint behind coloured text, watermark digit behind a card, text on
  a picture); the build's order, manifest, refusals (a changed slide, a replaced picture, another
  file, a broken record), image confinement and the schema check. Every check was broken
  on purpose (20 changes) and each made a test fail.

## Not verified
- Windows: text widths come from the emitter's font metrics (measured by upstream on Office for
  Mac fonts); PowerPoint on Windows may lay a line out a few pixels differently.
- The thresholds rest on decks from one model (deepseek-flash) and two briefs.

## Follow-ups
- #198: the tool and its instructions, the `engine` route in the evaluation, the measurement.
