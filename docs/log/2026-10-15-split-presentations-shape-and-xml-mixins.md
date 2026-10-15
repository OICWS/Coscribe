# tools/presentations.py split, part 8: shape tools and XML/animation mixins

Two more mixins on `ToolkitBase`, method bodies unchanged: `ShapeToolsMixin`
(`tools/office/pptx/shape_tools.py`: shapes, formulas, table cells, charts, hyperlinks, slide
delete, duplicate and reorder) and `XmlAnimationMixin` (`tools/office/pptx/xml_animation.py`: raw
XML read and edit, notes, transitions, animations, audio). 3,397 to 2,242 lines.

The ratchet lists the long functions and two python-pptx attribute names as new keys because
their qualified names changed with the move; the totals stay the same (`--accept-worse`). The
formula import inside `add_pptx_formula` was a relative import into `tools/` and now points
three levels up.
