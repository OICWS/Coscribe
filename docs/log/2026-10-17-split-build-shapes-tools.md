# `build_shapes_tools` split into two builders (shipped)

Why: #348 item 4. `build_shapes_tools` was 423 lines, the longest function in the repository.

## Shipped
- `tools/office/pptx/wrappers_shapes.py`: the slide-order, shape and formula tools moved into
  `_slide_and_shape_tools`, the table, chart and hyperlink tools into `_table_chart_link_tools`;
  `build_shapes_tools` merges the two dicts. Each builder is under 300 lines. A pure move: bodies,
  docstrings (the tool schemas) and the key order are unchanged.

## Not verified
- `tests/test_tool_schema_snapshot.py` fails in a cloud session on main as well (#252), so the
  snapshot was compared by CI only. `test_presentations_tool.py` and `test_office_golden.py` pass
  locally.

## Follow-ups
- The other functions over 300 lines: `create_app_lg`, `build_docx_tools`, `build_browser_tools`,
  the two routers, `build_xml_animation_tools` (see `docs/plan.md` item 0a).
