# tools.office.doc: the Doc artifact's source, read as blocks and changed one block at a time

## Purpose
Owns a Doc's source (decision 0025): a markdown file marked `coscribe: doc` in its front matter,
read as blocks with the lines each covers (`blocks.py`, markdown-it-py), the edits that rewrite only
the lines of the blocks named and refuse a block that changed since it was read, the chart block
(`chart.py`: a fenced `chart` block, a kind and a pipe table), a Doc on disk as the editor reads and
saves it (`files.py`), its kept versions in its side folder `name.doc/` (`history.py`) and what the
person changed since coscribe was told (`told.py`) and its comments, anchored to the text of their
block (`comments.py`). Does not own the routes (`web/routes/doc.py`),
the note to coscribe (`conversation/docs_edits.py`), the editor, the card or the exports (later steps of the design), nor Word files (`office/docx`).

## Public interface
`read_doc`, `is_doc`, `apply_edits`, `Doc`, `Block`, `Replace`, `Insert`, `Delete`, `Edit`,
`NotADoc`, `BlocksRefused`, `CALLOUTS`, `parse_chart`, `Chart`, and for the editor `read_doc_file`,
`save_doc_edits`, `DocFileChanged`, `DocVersionGone`, `remember_doc_version`, `restore_doc_version`,
`remember_doc_before_edit`, `doc_edits_since_told`, and for the comments `read_doc_comments`,
`add_doc_comment`, `reply_to_doc_comment`, `resolve_doc_comment`, `edit_doc_comment`,
`mark_doc_comment_sent`, `delete_doc_comment`,
`DocCommentNotFound`, `DocCommentRefused`. Import them from `coscribe.tools.office.doc`;
the server and the conversation reach them through `coscribe.tools`.

## Depends on
`coscribe.tools._chart_data`, `coscribe.tools._file_locks`.

## Invariants
- An edit changes only the lines of the blocks it names; every other line stays byte for byte, and a
  file's own line endings are kept.
- No non-blank line of the body is outside a block (a link reference definition is an `other` block).
- A replace or delete carries the text the caller read; if the block's text differs, nothing is
  written (`BlocksRefused`). A save also carries the version of the file the editor read, and a
  newer file refuses it (`DocFileChanged`).
- A Doc's versions and comments, and later its pictures, live in `name.doc/` beside it, so they
  travel with it; a comment is anchored to its block's text (and which copy of it), so it follows
  the block when blocks are added or removed, and is `detached` when the text is gone; the record of what the person changed lives in the state folder.
- `markdown-it-py` and `yaml` are imported inside the function that needs them (startup time).

## Tests
`tests/test_doc_blocks.py` (kinds, line ranges, every edit, CRLF, property tests that a replace
touches only its own lines and a replace by the same text changes nothing, the chart block),
`tests/test_doc_files.py` (read and save, versions, what the person changed),
`tests/test_doc_comments.py` (the comments and their anchors), `tests/web/test_doc.py`
and `tests/web/test_chat_doc_edits.py` (the routes and the note to coscribe).

## Verify by hand
A Doc written by a model in a real conversation read back as blocks (step 6 of the design).

## Reviewed
2026-10-26 (first card).
