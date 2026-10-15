# tools/presentations.py split, part 10: the entry point (shipped)

Why: batch 6 asked for `tools/presentations.py` to be under 1,500 lines.

## Shipped
- `PresentationToolkit` is its own module, `tools/office/pptx/toolkit.py` (the list of topic mixins).
- `build_presentation_tools` and its tool wrappers moved unchanged to
  `tools/office/pptx/tool_wrappers.py` (1,477 lines).
- `tools/presentations.py` keeps the module docstring and re-exports both names, so every importer
  and test stays as it was: 83 lines. Its entry in `tests/test_file_sizes.py` is gone.
- `quality/baseline.json`: the file-length, long-function and complex-function entries for the
  wrappers moved from `presentations.py` to `tool_wrappers.py` (`--accept-worse`, same numbers).

## Not verified
- `build_presentation_tools` is still one 1,464-line function; the ratchet keeps it listed.
