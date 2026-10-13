# pptx goldens cover templates and SmartArt edits (shipped)

Why: Part 2 of the pptx goldens (issue #89) needs every tool group covered before `tools/presentations.py` is split. This is the group of template tools and the SmartArt escape hatch (`edit_pptx_xml`).

## Shipped
- Five decks with goldens, 23 in all:
  - `template_fill_shrunk`, `template_fill_grown`, `template_fill_fixed_slides_only`: `extract_pptx_template` from a fixed reference deck built in the test (python-pptx's stock template: title, two content slides, closing), then `fill_pptx_template` with fewer, more and only-fixed chunks (a content slide dropped, duplicated, and all dropped). No bundled template is read, so editing a shipped template does not fail them.
  - `write_with_template_path`: `write_pptx` with `template_path`, which keeps the template's theme and drops its slides.
  - `smartart_text_edit`, `smartart_shape_attributes`: `edit_pptx_xml` on a SmartArt node's text, and with `set_attributes` on the frame.
- `tests/pptx_fixtures.py` holds the hand-built SmartArt deck, shared with `test_presentations_tool.py`. Its diagram parts now validate against `dml-diagram.xsd` (the old fixture had a point with a made-up connection id and empty layout and colour parts).
- A second shared golden, `_shared_4x3.txt`, holds python-pptx's stock 4:3 master, layouts and theme once, as `_shared.txt` does for the 16:9 one. The five new goldens are about 150 KB instead of 540 KB; the existing goldens are unchanged.
- Stability probe: all five built twice in separate processes (`PYTHONHASHSEED` 11 and 4242, three seconds apart, different folders). Every canonical deck was identical.

## Not verified
- Windows: only Linux was run. The nightly Windows job will show it.
- That PowerPoint opens the SmartArt fixture; the parts are schema-valid, which is as far as a script here can check.

## Follow-ups
- Audio and CJK text: see the next log entry.
