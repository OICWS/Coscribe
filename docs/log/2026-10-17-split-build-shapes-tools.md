# `build_shapes_tools` split into six builders (shipped)

Why: #348 item 4. `build_shapes_tools` was 423 lines, the longest function in the repository.

## Shipped
- `tools/office/pptx/wrappers_shapes.py`: the 13 tools are grouped, in order, into six builders
  of under 100 lines each; `build_shapes_tools` merges their dicts. A pure move: bodies, docstrings
  (the tool schemas) and the key order are unchanged. `quality/baseline.json`: `long_functions`
  42 to 41 (the 423-line entry is gone; the ratchet counts functions over 100 lines, so two
  builders over 100 would have been worse).

## Not verified
- `tests/test_tool_schema_snapshot.py` fails in a cloud session on main as well (#252), so the
  snapshot was compared by CI only. `test_presentations_tool.py` and `test_office_golden.py` pass
  locally.

## Follow-ups
- The other functions over 300 lines: `create_app_lg`, `build_docx_tools`, `build_browser_tools`,
  the two routers, `build_xml_animation_tools` (see `docs/plan.md` item 0a).
