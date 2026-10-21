# Docs: a .docx as blocks, saved block by block (backend, shipped)

Why: decision 0019. The Docs editor needs to read a Word file as blocks and write back only what
the person changed, without touching comments, tracked changes or what the editor does not model.

## Shipped
- `read_doc_blocks(path)`: the document as blocks (title, heading 1–3, paragraph, quote, bullet and
  numbered items to three levels, table of text cells) with bold, italic, underline and links, and
  the version of the file read (a hash). What the editor cannot change is a locked block with its
  reason and a text preview: comments, tracked changes, fields (contents), pictures and charts, notes,
  page and section breaks, internal links, merged or multi-paragraph tables.
- `save_doc_blocks(path, version, blocks)`: rewrites the blocks that differ from the file, creates
  new ones by style, removes the ones left out, and keeps the rest as they are, in the order sent. A save
  over a newer file raises `DocChanged`; a block that cannot be written raises `BlocksRefused` with a text
  safe to show (a link must be http, https or mailto; a missing style is named). The result is validated
  against the Word schema before the file is replaced.
- `GET` and `PUT /api/threads/{id}/docs/blocks`.
- Tests: reading, a save of what was read leaving every paragraph and part as it was, one changed paragraph,
  comments and tracked changes surviving an edit elsewhere, locked blocks, kind changes, new blocks,
  deletions, table cells, rows and columns, stale saves, refused input, contents, pictures and charts.

## Not verified
- A saved document opened in real Word on Windows (the schema check and python-docx reopen pass).
- Documents made by Word itself with unusual styles or numbering; a missing List or Quote style is refused, not repaired.
- Column removal in a table is by position (the last column goes, the text of the others is rewritten).
- Nothing in the app calls the routes yet: the editor panel is the next step.
