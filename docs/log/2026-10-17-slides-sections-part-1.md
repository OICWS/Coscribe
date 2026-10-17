# Slides step 1, part 1: positioned HTML sections compile to native PowerPoint objects (shipped, unused)

Why: decision 0015 makes a slide one positioned HTML section, so the app can edit it in place;
the route replaces the SVG pages only if the deck evaluation says it is at least level (issue #392,
PR 1 of 4). This part is the language and the compiler; nothing calls it yet.

## Shipped
- `tools/office/pptx/engine/section_format.py`: the section language.
  - A `<section>` of well-formed XHTML on a 1920 × 1080 canvas.
  - Top-level elements: `h1`–`h3`, `p`, `ul`/`ol`, `x-shape`, `img`, `svg` and `aside` (notes).
  - Each element is positioned by `left`, `top`, `width` and `height` in px.
  - A closed set of attributes and styles per element. No `em`, `%`, `var()`, `margin` or
    classes, no event attributes, no URLs.
  - Inside a drawing: no `<script>`, `<style>`, `foreignObject`, links or animation elements, no
    `style` or `class` attributes, and `url()` only to the drawing's own definitions.
  - Every refusal says what to write instead.
- `text_layout.py`: line breaking as PowerPoint and the browser do it.
  - Breaks at spaces and between CJK characters; never before closing punctuation or after
    opening punctuation.
  - Widths come from the same per-face advances the SVG route uses (Windows-measured YaHei,
    Arial).
  - Breaks at 97% of the width, so a line that only just fits here does not wrap once more in
    PowerPoint.
- `text_box.py`: each text element becomes a PowerPoint text box with `wrap="square"`, so a
  paragraph reflows when edited in PowerPoint.
  - Exact line spacing, so the height is known and checked.
  - Bold, italic, underline, colour and size per run.
  - Bullets (`buChar`) and numbering (`buAutoNum`).
  - A box taller than its text is drawn at the text's height (top, middle or bottom of the box,
    as `vertical-align` says) and grows when edited (`spAutoFit`).
  - Text that needs more height than its box is an error that names both heights.
- `sections.py`: `compile_sections` and `check_sections`.
  - Shapes, pictures (`object-fit` cover, contain or fill) and embedded SVG drawings are turned
    into the SVG page language and converted by the existing emitter, scaled from the
    1920-wide canvas. They get the same page checks and come out as the same native shapes.
  - The slide is 13.333 × 7.5 in (1 px = 1/144 in, 6,350 EMU).
  - `id="title"` becomes the title placeholder, `background` the slide background, and
    `<aside>` the speaker notes.
- `checker.py`: `check_deck(..., emu_per_px=)`, so a finding names the coordinates the source
  has (1920-wide for sections). The SVG pages' results are unchanged.
- `compiler.py`: the helpers the section compiler shares are public (`convert_element`,
  `attach_relationships`, `make_title_placeholder`, `PAGE_CHECKS`, `NSDECL`).
- `scripts/sections_wrap_check.py` writes a deck of tinted boxes, each exactly as tall as the
  compiler says its text needs, to check PowerPoint's line breaks by eye.
- `tests/test_deck_sections.py`: 22 tests.
  - Native objects and slide size.
  - Wrapping, exact spacing, runs and lists.
  - A box drawn to its text's height, and the overflow error.
  - Coordinates in the checker's findings.
  - Thirteen refusals, and spaces at line ends dropped as in HTML.
  - Line breaking, punctuation rules and long words.

## Not verified
- PowerPoint's own line breaks on Windows: the overflow check is only as good as they match
  `text_layout`. Open the deck `scripts/sections_wrap_check.py` writes: text below a tinted box
  is a mismatch. LibreOffice here (substituted fonts) keeps every paragraph inside its box.

## Follow-ups
- Part 2: `table`, `x-chart`, `x-icon`, transitions and build-ins, the deck folder with per-slide
  hashes.
- Part 3: the tool takes a folder of sections, the "Slides" skill, the evaluation's switch.
- Part 4: the measurement against the SVG pages.
