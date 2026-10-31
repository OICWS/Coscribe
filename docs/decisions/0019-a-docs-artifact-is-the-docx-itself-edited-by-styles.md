# 0019: A Docs artifact is the .docx itself, edited in the app block by block, by styles not fonts

Status: accepted (2026-10-21, by the maintainer, with the research in
`docs/assessments/2026-10-21-docx-editing.md`: Tiptap 3 for the editor, the block reader and writer
our own). Builds on 0013 (house style) and 0015 (what coscribe makes is an artifact). Narrowed by
0025 (a new Doc is a markdown document, not a .docx) and 0027 (a Word file is no longer edited in
the app): what is left is that a Word file coscribe writes keeps its styles.

## Context
Claude has two things: an online Docs object (rich text in the cloud, exported to Word on demand)
and a .docx from a skill (a download with no preview or editing). It needs both because the cloud
has no folder of the user's. coscribe runs on the user's computer, so the artifact can be the
real file and the app can edit it. A source file beside the .docx (as a deck has its pages) was
considered and dropped: the Word panel's comments and tracked changes, and the person's own edits
in Word, change the .docx directly and would leave such a source stale.

## Decision
- **A Docs artifact is the `.docx` in the workspace**, nothing beside it. Word opens it; the app
  previews, comments on and edits it.
- **The editor reads the file as blocks** (Heading 1–3, paragraph, quote, list item, table, image,
  divider, page break, contents) with bold, italic, underline and links inside them. Anything else
  (text boxes, fields, equations, section breaks) is a locked block the editor shows and keeps as it is.
- **A save rewrites only the blocks the person changed**, in the file, by style. Untouched blocks,
  comments and tracked changes stay byte for byte (0015: only what was edited can lose anything). A
  block holding a comment anchor or a tracked change is locked; it changes through the review actions.
  Direct formatting in an edited paragraph (a font, a colour) gives way to the style.
- **The person's Word edits are never overwritten**: a save carries the file version the editor read,
  and one made over a newer file is refused and the editor reads it again, as a slide save is.
- **The app offers styles, not fonts**: Normal, Heading 1–3, Quote; bold, italic, underline; lists;
  links; tables with rows and columns added and removed; images; divider, page break, contents. No
  font, size, colour, margin, column or header editing in v1; Open in Word covers those.
- **The editor is a rich-text editor whose schema is exactly that set** (a ProseMirror-based library,
  chosen and checked live when it is added). Saves go through the backend (0014). The person's edits
  and undos reach coscribe at the start of its next turn, never through a tool schema (0001), and
  undo covers coscribe's turns, as in Slides.

## Consequences
- No change to `write_docx` or any tool schema: the editor uses its own routes.
- A document made in Word can be edited the same way; whether the app offers it for files that are
  not artifacts is a product choice, as it was for decks (they stay read-only).
- Version history for documents is wanted and not in v1.
- Order: the block reader and writer (backend), then the editor panel, then the hand-offs to coscribe.
