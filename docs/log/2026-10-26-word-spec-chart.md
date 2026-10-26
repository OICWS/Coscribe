# Word spec, step 2: the chart component and the markers read back

Date: 2026-10-26
Area: tools

Step 2 of decision 0024. A spec's `:::chart <type> <title>` component writes a native Word chart
(the code `add_docx_chart` uses) from a pipe table of data, centred at the width of the text, with
an optional `caption:` line in the Caption style. A type that is not `bar`, `line` or `pie`, a
non-numeric cell and a pie with more than one data column are refused with what to change.

The reader (`read_doc_blocks`) now says which component wrote a block: a `component` field
(`cover`, `stats`, `callout_warn`, `chart`, `figure`...) from the `cs_` bookmark the compiler leaves
in it. The editor ignores it for now; the checker (step 3) and the in-place editing of components
(step 6) use it.

Not verified: the chart in real Word on Windows (its data workbook opens through "Edit data" in
Word; checked here against the schema and by reading the file back).
