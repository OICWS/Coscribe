# 0025: The Doc artifact is a markdown document, and the Word panel is frozen

Status: proposed (2026-10-26), for the maintainer to accept. Design and steps:
`docs/assessments/2026-10-26-doc-artifact.md`. Extends 0015 (comments live beside the file) and
0019 (the .docx is the artifact, which stays true for Word files); changes neither for the files
they cover. Follows 0024 (not adopted).

## Context
Drawing an arbitrary .docx in the app has no end, and the Word route (`write_docx` from markdown)
is steady and is kept. A spec route for Word was built and measured (0024) and did not beat
markdown. What the app lacks is a document people and coscribe write together, like an article:
content and structure first, few styles, precise edits, comments, export. An HTML artifact is a
page, its content is code, and it does not fit.

## Decision
- A **Doc** is an artifact whose source is a markdown file marked `coscribe: doc` in its front
  matter, with a folder beside it for comments, pictures and kept versions.
- The format is commonmark and GFM plus two additions a model already writes: `[!NOTE]`-style
  call-outs and a fenced `chart` block with a pipe table. No colours, fonts or sizes in the source.
- coscribe edits it with the ordinary file tools; the person edits it in the Docs editor, which
  rewrites only the blocks that changed. Comments for coscribe work as a deck's do.
- Exports: Markdown, PDF through the browser's print dialog, Word through `write_docx`.
- The Word panel is **frozen**: it keeps opening .docx files, takes bug fixes only, and gets no
  effort to draw more of a .docx. Removing it is a later decision.
- coscribe writes a Doc when the person asks for a document to keep in the app, and a .docx when
  they ask for a Word file, give a template or a file to edit.

## Consequences
- No more work on faithful .docx drawing; the open gaps in it (contents leaders, headers and footers
  in the editor) stay open.
- `markdown-it-py` becomes a declared dependency; no LibreOffice, no new runtime.
- A model must learn two additions; whether it does without being told is measured before the
  skill makes a Doc the default (step 6 of the design).
- Real-time editing by several people is not part of this; the format does not prevent it later.
