# Slides step 2, part 2: a deck mixes SVG pages and sections; one slide converts (shipped, unused)

Why: decision 0016 turns a slide into a section when the user first edits it, so a deck's folder
holds SVG pages and sections side by side, and one slide must convert without touching the
others (issue #414, PR 2 of 2).

## Shipped
- `build_deck` builds a folder of `.svg` pages and `.html` sections, one file per slide, in
  file-name order. Two files for one slide (`03.svg` and `03.html`) are refused, and so is a
  template in a deck with sections.
- `compile_sections` takes SVG pages among its sections and compiles them as `compile_pages`
  does (`add_page`, pulled out of `compile_pages`). Their canvas must be 1280×720, the page size
  of the sections' slide.
- `check_deck` takes one unit per slide, so a finding names the px of the slide's own source.
- `convert_slide(page)` writes the section next to the page and removes the page.
- `built_pages` gives None for a deck with a section. The preview then draws the .pptx, because
  resvg draws only SVG pages.
- Tests: a three-slide deck built, its middle slide converted and rebuilt, has the same texts
  and shapes; a slide held by two files is refused.

## Not verified
- PowerPoint on Windows: nothing new is written into the slides, so this needs no check of its
  own beyond part 1's.

## Follow-ups
- The read-only Slides panel: an unedited slide drawn from its SVG page, an edited one from its
  section.
