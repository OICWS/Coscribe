# pptx goldens cover templates and SmartArt edits (shipped)

Why: Part 2 of the pptx goldens (issue #89) needs every tool group covered before `tools/presentations.py` is split. This is the group of template tools and the SmartArt escape hatch (`edit_pptx_xml`).

## Shipped
- Six decks with goldens, 24 in all:
  - `template_fill`: `fill_pptx_template` on the bundled `bold-statement` template, shrinking its four slides to three.
  - `template_fill_grown`: the same template grown to six slides (slide duplication).
  - `write_with_template_path`: `write_pptx` with `template_path`, which keeps the template's theme and drops its slides.
  - `template_extracted_then_filled`: `extract_pptx_template` from a reference deck, then `fill_pptx_template` with the new custom template.
  - `smartart_text_edit`: `edit_pptx_xml` on the text of a SmartArt node (the linked data part).
  - `smartart_shape_attributes`: `edit_pptx_xml` with `set_attributes` on the SmartArt frame itself.
- SmartArt cannot be created by any library, so those two decks start from the hand-written fixture the tool tests already use (`_write_smartart_fixture`, imported rather than copied).
- Stability probe: all six built twice in separate processes (`PYTHONHASHSEED` 11 and 4242, three seconds apart, different folders). Every canonical deck was identical.

## Not verified
- Windows: only Linux was run. The nightly Windows job will show it.

## Follow-ups
- The new goldens are large (about 540 KB for six): the SmartArt decks and the templates carry python-pptx's 4:3 master and layouts, which differ from the 16:9 ones `_shared.txt` holds. A second shared golden for the 4:3 master would cut most of that; it changes how goldens are stored, so it is for the maintainer to decide.
- Last group: audio and CJK text.
