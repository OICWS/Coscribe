# tools/presentations.py split, part 6: the toolkit's module-level helpers

The module-level helpers of `presentations.py` (hyperlink and XML argument validation, shape
and table lookup, icon recolouring and the icon set, the delivery analysis, the PDF render, the
shape type list) moved to `tools/office/pptx/toolkit_helpers.py` unchanged, names public. The
toolkit and the wrappers reach them through one module import (`th`). 4,259 to 3,856 lines.

The icon directory is now found with `parents[3]` from the new file, and the test fixture that
turns off LibreOffice rendering patches `toolkit_helpers.render_to_pdf`. `analyze_pptx_delivery`
is as complex as before (17) but is a new name to the ratchet: `--accept-worse`.
