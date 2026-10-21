# 0019: A Docs artifact is the .docx itself, edited in the app by styles, not fonts

Status: proposed (2026-10-21). The maintainer agreed the direction in conversation; this record
waits for acceptance. Builds on 0013 (house style) and 0015 (what coscribe makes is an artifact).

## Context
Claude has two things: an online Docs object (rich text in the cloud, exported to Word on demand)
and a .docx from a skill (a download with no preview or editing). It needs both because the cloud
has no folder of the user's. coscribe runs on the user's computer, so the artifact can be the
real file and the app can edit it.

## Decision
- **A Docs artifact is the `.docx` in the workspace.** There is no second, in-app document format.
  Word opens it; the app previews, comments on and edits it.
- **A source folder sits next to it**, as a deck's pages folder does: the document in the markdown
  subset `write_docx` takes (headings 1–3, paragraphs, bold, italic, lists, tables, `[TOC]`), later
  with underline, links, images and page breaks. Its record names the .docx by path and holds the
  hash coscribe last wrote. Edits change the source and compile it with the house style (0013).
- **The person's Word edits are never overwritten.** If the .docx no longer matches the recorded
  hash, the editor does not save: coscribe offers to change it through the conversation, or to start
  from the Word version (read back into the source; what the subset cannot hold is lost, and the
  person is told so first). A document coscribe did not write has no source and is shown read-only.
- **The app offers styles, not fonts**: Normal, Heading 1–3, Quote; bold, italic, underline; lists;
  links; tables with add and remove of rows and columns; images; divider, page break, contents. No
  font, size, colour, margin, column or header editing in v1; Open in Word covers those.
- **The editor is a rich-text editor whose schema is exactly that subset** (a ProseMirror-based
  library; chosen and checked live when it is added). Saves go through the backend (0014).
  The person's edits and undos reach coscribe at the start of its next turn, never through a tool
  schema (0001), and undo covers coscribe's turns, as in Slides.

## Consequences
- Extending the markdown subset changes `write_docx`'s description: its own reviewed PR (0001).
- A Word-made or Word-edited document is read-only in the editor; comments and tracked changes on
  it keep working in the Word panel.
- Version history for documents is wanted and not in v1.
- Order: the source and its compiler, then the editor panel, then comments and the AI hand-offs.
