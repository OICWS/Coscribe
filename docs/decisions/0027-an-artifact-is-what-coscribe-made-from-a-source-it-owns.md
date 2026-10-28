# 0027: An artifact is what coscribe made from a source it owns

Status: accepted (2026-10-28, by the maintainer). Narrows 0019 and 0025 (a Word file is no longer
edited in the app) and 0014 (an Excel file is not an artifact).

## Context
The Artifacts page listed every Word, Excel and PowerPoint file a conversation created or replaced,
and a Word file opened in an editor of its own (Tiptap over the file's XML). That editor was the
largest source of fidelity bugs: a paragraph with a Word comment was locked, a table lost its
style, a contents list was drawn two ways. Word and Excel do this better, and the people who use
coscribe have them. The other agent the maintainer compared with (Claude) keeps a `.docx` or
`.xlsx` as a download, not an artifact, and its artifacts are things it can open and edit itself.

## Decision
- **An artifact is what coscribe made and the app can open and edit from a source it owns**: a Doc
  (Markdown), a deck coscribe built (its pages are the source; the `.pptx` is the export), a design,
  a design system.
- **A `.docx` or `.xlsx` is a file**, for Word or Excel. It is not listed on the Artifacts page, has
  no card, and does not open in an editor of the app. The tools still read and write them.
- **A deck the person brought is theirs.** Only a `.pptx` the conversation created is an artifact; one
  that was read, edited in place or replaced whole is not.
- "Make something new" offers Docs, Slides, Design, Dashboard (a direction, "Soon") and Design
  system; it has no Sheets. A table to look at in the app is a Dashboard (HTML, CSS, JavaScript).
- **Which form a piece of writing takes is the model's decision**, from the skills' descriptions, not
  the person's: a Doc for writing to keep, edit or send, a Word file when Word, a template or tracked
  changes is asked for, an answer in the conversation otherwise.

## Consequences
- Taken out in steps: the listing rule (this record's first PR), then the Word editor and the
  Word panel's menu (the second), then the `sheets` kind in the wire types, the Artifacts tool and
  the page.
- A Doc exported to Word stays: it is a file the person asked for.
- Files already in the registry that are no longer artifacts stay in its file and are not listed.
- A person who asks coscribe to change their own Word file sees the result in Word.
