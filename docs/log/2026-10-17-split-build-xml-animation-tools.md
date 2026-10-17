# `build_xml_animation_tools` split into five builders (shipped)

Why: #348 item 4. `build_xml_animation_tools` was 328 lines, over the 300-line exit criterion.

## Shipped
- `tools/office/pptx/wrappers_xml_animation.py`: the 8 tools are grouped, in order, into five
  builders of at most 100 lines; `build_xml_animation_tools` merges their dicts. Bodies,
  docstrings (the tool schemas) and the key order are unchanged. The one change that is not a move:
  `add_pptx_animation` passes its arguments to the toolkit by position instead of by keyword (same
  order as the toolkit's signature), so its builder stays at 100 lines for the ratchet.
- `quality/baseline.json`: `long_functions` 41 to 40.

## Not verified
- The schema snapshot is checked by CI only (it fails in a cloud session on main, #252).
  `test_presentations_tool.py`, `test_office_golden.py` and `test_pptx_*.py` pass locally.

## Follow-ups
- Left over 300 lines: `create_app_lg`, `build_docx_tools`, `build_browser_tools`, the two routers.
