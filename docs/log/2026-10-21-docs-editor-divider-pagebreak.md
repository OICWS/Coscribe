# Docs editor: a divider and a page break (shipped)

Why: both are ordinary parts of a Word document and were either missing (divider) or a grey locked line
(page break), so a document could neither be written with them nor edited around them.

## Shipped
- "/" offers **Divider** and **Page break** (typing "divider", "line", "separator", "new page" finds them).
  Each is a block of its own in the editor: a thin line, and a dashed line labelled "Page break". An empty
  paragraph follows, so typing goes on.
- In the file a divider is an empty paragraph with a bottom border, a page break an empty paragraph holding
  one page break (`block_breaks.py`). The reader takes exactly those two shapes: a paragraph with text and
  a border is text, a page break inside a sentence stays a locked block, so nothing already in a file is
  rewritten differently than before.
- A picture added from a file also gets the empty paragraph after it.
- Tests: reader and writer (inserted, read back, sent back unchanged, deleted; the two look-alikes stay as
  they were), vitest (blocks both ways, "/" matching), Playwright ("/divider", "/page", written to the file).

## Not verified
- How Word draws the rule (a thin bottom border, the style's colour) and a page break inside a list or a
  table cell (a cell is not offered the menu).
- The packaged app on Windows.

## Follow-ups
- Picture size and alt text, undo across coscribe's turns: in `docs/plan.md`.
