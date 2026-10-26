# Word charts: a colour per bar and Word's axis range

Date: 2026-10-26
Area: frontend

The chart drawn for a Word file (`lib/docxChart.ts`) used one colour for a single series and went one step
past Word on the value axis. A single series now gets a colour per bar or slice unless the file sets
`varyColors` to 0, a point's own fill is used, and the axis stops at the first round step past the data
(at most ten steps, or the range and step the file fixes).

Not verified: charts other than the bar chart `add_docx_chart` writes; Word's own gridline and font styling.
