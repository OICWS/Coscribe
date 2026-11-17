# The AI saves tables across pages as CSV and pages as PDF (shipped, part 3 of #915)

Why: taking data off a site meant reading snapshots and retyping rows, one page at a time, and a
page could not be kept as a document, in conversations and saved workflows alike (#915).

## Shipped
- `browser_save_table(table, path, next_page, scroll, max_pages)`: a table or list as rows, found
  by a text it holds (a column header), since tables carry no refs in a snapshot; empty takes the
  largest table. Spanned cells fill every column they cover; header rows become the header. A list,
  or a grid of cards built from plain elements (the nearest ancestor with at least two more of its
  kind), gives one row per item, its lines as columns and its link first.
- Across pages: `next_page` is clicked until it is gone, disabled or the table stops changing;
  a bare ref is turned into its snapshot description first, because the page redraws or reloads
  the button. `scroll` loads more until the list stops growing (at most 10 s per round), skipping
  rows already read. At most 100 pages and 50,000 rows; the result says when it stopped early.
- With `path` the rows go to a UTF-8 CSV with a BOM, so Excel opens Chinese text right. A cell
  that starts with = + - @ and is not a number gets a leading `'`: Excel would run it as a formula a
  page planted. A workbook comes from `write_xlsx_cells(from_csv=...)`, which owns how workbooks
  are written (decision 0011). Without `path` the rows come back as text.
- `browser_save_pdf(path, landscape)` prints the page with its backgrounds.
- Both are WRITE_LOCAL and keep an existing file, writing "name (1).csv" instead, so a daily
  workflow keeps every day's file; a workflow reads the name from `{{<save_as>.file}}`, which the
  drafting prompt says. Drafting turns bare refs in `next_page` and `target` into descriptions too,
  and refuses a draft that keeps one.
- Tests: `scripts/browser-native.cjs` (real Electron) collects a table over three pages whose Next
  button is redrawn each time, with a spanned header and cell, reads a scrolling list to its end
  and prints a PDF; its overall limit goes from 50 s to 70 s. pytest covers the tools, the CSV
  guard, file names, the drafting check and a saved workflow that collects a table and passes the
  file on.

## Not verified
- A person using the Windows app; real sites with server-side paging that reloads the page, and
  tables inside iframes (only the page itself is read).

## Follow-ups
- Part 4 of #915: acting from a screenshot, healing for the newer tools, a login lost mid-run,
  watching a page for changes.
