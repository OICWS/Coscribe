# A Design page shows a picture file of its canvas folder; the skills place a system's logo (step 3)

Why: step 2 (`docs/log/2026-11-03-design-system-assets-start.md`) copies a design system's
pictures into the workspace. Two things were still missing: a Design page could not show a file
at all (its frame loads only `data:` URIs), and neither skill said where a logo goes.

## Shipped
- **Pictures in Design pages** (`design_canvas.with_pictures`, called from `served_page` after
  the parts are filled in):
  - The server replaces an `<img src>` or SVG `<image href>` that names a picture file of the
    canvas folder (or of a folder inside it) with that file as a `data:` URI. Parts get the same.
  - The canvas, Play, the HTML/PDF/PNG export and `look_at_page` all show the picture.
  - A path that leaves the folder, a missing file and any address are left as written, so a look
    at the page shows the gap.
  - The pictures filled into one page add up to at most 12 MB.
- **The Design skill:**
  - A picture file is copied into the canvas folder with `copy_file` and named by its file name.
    Nothing loads from outside the canvas folder.
  - A design system's logo goes where a brand belongs, in the variant its note asks for, and is
    never redrawn, recoloured or stretched.
- **The Slides skill** (`pptx-pages`): the logo is copied into the pages folder and placed with
  `<image href>` where its note says.
- **Tests:** `tests/test_design_canvas.py` covers a page's picture and a part's picture filled
  in, an SVG `<image href>` in a subfolder, and three that are left as written: `../`, a missing
  file and an address.

## Not verified
- Not run with a real model; step 4 measures it with DeepSeek.
- Checked on Linux only.
