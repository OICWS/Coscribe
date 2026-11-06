# A design system's logo and pictures measured with DeepSeek: 4 of 4 tasks as intended (shipped)

Why: four changes shipped untried with a real model:
- the deck build's logo warning and its seeding of the conversation's system
  (`docs/log/2026-11-05-unplaced-logo-warning.md`);
- a picture beside the pages not counted as a slide;
- `look_at_page`'s note (`docs/log/2026-11-05-design-logo-note.md`);
- pictures added from "describe it" and a template
  (`docs/log/2026-11-05-design-system-assets-from-sources.md`).

This run tries them with DeepSeek (`deepseek-flash`, `reasoning_effort` low), off-peak, one
run per task, four tasks at once.

## Measured
- **Slides deck** (six slides, started with the Tidewater system: a light logo, a reversed logo
  and an app icon):
  - `logo.svg` and `logo-reversed.svg` were copied straight into the pages folder and placed.
    The reversed logo is on the teal cover, the light one on the closing slide.
  - The build counted 6 slides, not 8. The logo files were pictures, not pages; the last run
    had to move them into `assets/` to get past this.
  - Both slides keep the SVG itself (`asvg:svgBlip`).
  - `design-system.json` was seeded at the first build.
  - No logo warning in 6 builds, which is right because the logo was placed. Whether the
    model acts on the warning when it does fire is still not measured.
- **Design landing page** (desktop and phone):
  - Both logos were copied into the canvas folder: the light one in the header, the reversed
    one on the dark footer (a shared part).
  - `look_at_page` could not draw in this container (its browser times out, on `main` too).
    Its note was neither shown nor needed, since the logo was placed.
- **"Describe it" with two attached logos:**
  - The system was saved with both as logos, 240x64.
  - Each note says where it goes ("on white and foam backgrounds only", "on ink and teal
    backgrounds only").
  - 31 s, one `save_design_system` call.
- **From a template** (a .pptx whose two layouts draw the same 240x64 picture):
  - `read_pptx_design` listed it once, on both layouts.
  - It was saved as the system's logo with a note on where it sits.
  - The model told the user that this "logo" is only a plain teal block, which is true of this
    test picture.

## Seen in passing
- In LibreOffice, two of the deck's slides show a heading over its body text. The pages ask for
  Segoe UI, which this Linux container does not have, and LibreOffice's substitute is wider, so
  the lines wrap more. This is not part of the logo work and was not checked in PowerPoint.

## Not verified
- The deck's logo warning firing in a real run, and the model fixing it: the model placed the
  logo every time.
- `look_at_page` in this container (browser).
- One run per task. Linux only.
