# tools/presentations.py split, part 5: the Markdown slide builders

The functions that turn `write_pptx`'s Markdown chunks into slides (bullet, table, icon list, stat
callout, two column, the layout directive, the content area and the stock layout widening) and
their constants moved to `tools/office/pptx/slide_builders.py` unchanged, names public.
`presentations.py` imports them back under their old private names, so the toolkit and the tests
read the same. 4,979 to 4,259 lines; the toolkit class and the tool wrappers are what is left.

The dead-code ratchet counts python-pptx attribute assignments per file, so the moved ones show
as new in the new file and gone in the old: net +3 names in the baseline, needs `--accept-worse`.
