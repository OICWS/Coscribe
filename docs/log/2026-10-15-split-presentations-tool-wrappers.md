# tools/presentations.py split, part 11: the tool wrappers by topic (shipped)

Why: after part 10 the 39 deck tool wrappers were still one 1,464-line function,
`build_presentation_tools`.

## Shipped
- The wrappers moved unchanged into five modules under `tools/office/pptx/`, one function each:
  `wrappers_review` (read, preview, delivery, theme colours), `wrappers_templates` (write, fill,
  extract, edit text), `wrappers_shapes` (slides, shapes, formulas, tables, charts, hyperlink),
  `wrappers_images` (images, icons, background, scrim, effects), `wrappers_xml_animation` (XML,
  notes, transitions, animation, audio).
- `tool_wrappers.build_presentation_tools` (88 lines) builds the toolkit, collects the five groups
  and returns the 39 tools in the old order with the old risk categories (`_TOOLS`). The order is
  fixed because the tool list is provider-cached.
- Checked by dumping every returned tool before and after (name, signature, docstring hash,
  metadata, order): byte-identical.
- Ratchet: the 1,464-line function is gone; five functions of 178 to 423 lines are listed instead
  (`--accept-worse`, the long-function count is 4 higher, the longest one 1,041 lines shorter).

## Not verified
- Nothing platform-specific. `test_tool_schema_snapshot` only runs in CI (#252).
