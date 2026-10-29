# A Doc's Word file keeps italics, code and links, and its charts look like the Doc's (shipped)

Why: the maintainer's sample Doc was rendered both ways, in the panel and as its Word export through
LibreOffice, and the export differed:
- `*斜体*` came out with its asterisks. Python counts a Chinese character as a word character, so
  the "not glued to a word" rule never matched in Chinese.
- `` `order_id` `` and `[text](url)` came out as their markers too: the writers had no code span
  and no link.
- The sentence introducing a chart ("构成比例用饼图，只需要一列数值：") ended page 2 alone, and the
  chart opened page 3 after half a blank page.
- Charts took Office's default colours instead of the panel's, and a single-series line chart had a
  legend (the line template brings its own).

## Shipped
- `markdown_blocks.parse_inline_spans`: bold, italic, `code` and `[text](url)`. Next to an asterisk
  only a Latin letter or a digit counts as a word, so Chinese italics work and `2*3*4`,
  `snake_case` stay as they are. `parse_inline_runs` (PowerPoint, PDF, table cells) is built on it:
  a code span and a link's words are plain text there.
- Word: code in Consolas on a grey ground, a link as a real hyperlink.
- Word: a paragraph ending in a colon keeps with what follows.
- Doc export: charts in the panel's colours (`_CHART_COLOURS`); no legend for one series. `write_docx`
  keeps the theme's colours.
- The CJK golden changes: its `*持平*` is now italic, as intended.

## Not verified
- In the real Word on Windows; rendered with LibreOffice only.
