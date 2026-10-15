# tools/presentations.py split, part 9: the template and review mixins

The last toolkit methods moved into two mixins on `ToolkitBase`, bodies unchanged:
`TemplateToolsMixin` (`tools/office/pptx/template_tools.py`: write a deck, fill and extract a
template, edit text, plus the widescreen width and template id constants they use) and
`ReviewToolsMixin` (`tools/office/pptx/review_tools.py`: read, preview, delivery check, theme
colours). `PresentationToolkit` is now only the list of mixins. 2,242 to 1,569 lines; what is
left in `presentations.py` is `build_presentation_tools`, the tool wrappers.

The ratchet lists four long or complex functions and one attribute name as new keys because
their qualified names changed with the move; the totals stay the same (`--accept-worse`).
