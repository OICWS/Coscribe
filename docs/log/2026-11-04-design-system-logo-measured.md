# A design system's logo measured with DeepSeek; a deck page takes an SVG picture (step 4)

Why: step 3 (`docs/log/2026-11-03-design-system-assets-use.md`) tells both skills to place a
design system's logo. This step measures it with a real model (DeepSeek, `reasoning_effort`
low). The system was "Tidewater", with three SVG assets: a logo for light backgrounds, a reversed
logo for dark ones, and an app icon for small square spots only. There were two briefs: a Design
landing page (desktop and phone) and a six-slide Slides deck.

## Measured
- **Design, 2 of 2 boards:**
  - Both logos were copied into the canvas folder unchanged.
  - The light logo goes in the header. The reversed logo goes on the teal quote band and the dark
    footer, as the notes say.
  - The app icon was not used.
  - The pictures show on the canvas, filled in as `data:` URIs.
- **Slides, 6 of 6 slides have the logo:**
  - The light logo goes top left on the five light slides; the reversed logo on the dark closing
    slide.
  - The first build failed: `build_pptx_from_pages` crashed on `<image href="logo.svg">`.
    python-pptx opens every picture with Pillow, and Pillow cannot read an SVG.
  - The model then drew the logo again as a PNG with PIL. The wave came out jagged and the
    lettering in another font. That is what the skill forbids, and the cause was the engine, not
    the model.

## Shipped
- **An SVG picture on a deck page** (`_native_svg/.../elements.convert_image`,
  `engine/compiler.attach_relationships`):
  - The slide keeps the SVG file itself as an `asvg:svgBlip` (MS-ODRAWXML). PowerPoint 2016 and
    later draw it as a vector.
  - The blip embeds a PNG of the same SVG, drawn by resvg at four times the picture's size. Older
    readers and LibreOffice draw that.
  - One SVG used on many slides is stored as one part.
  - The run's six pages, rebuilt with their `<image href="assets/logo.svg">`, give a deck whose
    LibreOffice render shows the logo on every slide.
- **Test:** `tests/test_deck_engine.py` checks an SVG picture: the PNG fallback at 4x, and the
  svgBlip naming an `image/svg+xml` part that holds the very file.

## Not verified
- The vector SVG in real PowerPoint on Windows: only LibreOffice (which draws the PNG fallback)
  and python-pptx were checked here.
- One run per brief. The run's cost was not recorded (the script's counter read 0).

## Follow-ups
- A build warning when a deck or board from a system with a logo places none.
- Assets added from "describe it" and from a template .pptx.
