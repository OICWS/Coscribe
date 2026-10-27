# tools.office.doc: the Doc artifact's source, read as blocks and changed one block at a time

## Purpose
Owns a Doc's source (decision 0025): a markdown file marked `coscribe: doc` in its front matter,
read as blocks with the lines each covers (`blocks.py`, markdown-it-py), the edits that rewrite only
the lines of the blocks named and refuse a block that changed since it was read, and the chart block
(`chart.py`: a fenced `chart` block, a kind and a pipe table). Does not own the routes, the comments,
the editor, the card or the exports (later steps of the design), nor Word files (`office/docx`).

## Public interface
`read_doc`, `is_doc`, `apply_edits`, `Doc`, `Block`, `Replace`, `Insert`, `Delete`, `Edit`,
`NotADoc`, `BlocksRefused`, `CALLOUTS`, `parse_chart`, `Chart`. Import them from
`coscribe.tools.office.doc`. Nothing in the app calls them yet: step 1 of the design.

## Depends on
`coscribe.tools._chart_data`.

## Invariants
- An edit changes only the lines of the blocks it names; every other line stays byte for byte, and a
  file's own line endings are kept.
- No non-blank line of the body is outside a block (a link reference definition is an `other` block).
- A replace or delete carries the text the caller read; if the block's text differs, nothing is
  written (`BlocksRefused`).
- `markdown-it-py` and `yaml` are imported inside the function that needs them (startup time).

## Tests
`tests/test_doc_blocks.py` (kinds, line ranges, every edit, CRLF, property tests that a replace
touches only its own lines and a replace by the same text changes nothing, the chart block).

## Verify by hand
A Doc written by a model in a real conversation read back as blocks (step 6 of the design).

## Reviewed
2026-10-26 (first card).
