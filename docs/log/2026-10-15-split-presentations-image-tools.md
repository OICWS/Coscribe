# tools/presentations.py split, part 7: the toolkit gets a base class and an image mixin

`PresentationToolkit` now inherits from `ToolkitBase` (`tools/office/pptx/toolkit_base.py`: the
workspace scope, the readable and writable path checks, `_open_slide`) and from
`ImageToolsMixin` (`tools/office/pptx/image_tools.py`: image replace and crop, icons, picture,
background image, scrim and shape effect). The method bodies moved unchanged, so the tool names,
signatures and the tests that call them are the same. 3,836 to 3,397 lines.

Later parts move the other topics (XML and animation, charts and tables, template handling) the
same way, each as a mixin on `ToolkitBase`. The dead-code ratchet needs `--accept-worse` for two
python-pptx attribute names that are new keys in the new file.
