# Design note: the Doc artifact (proposed)

Date: 2026-10-26
Area: docs

After the Word spec route was measured and not adopted, the maintainer's direction: no native .docx
preview work; Word files stay on the markdown route; Artifacts gets a Doc, a markdown document
that people and coscribe edit together, like Claude's online Docs, with comments for coscribe as on
a deck and export to Markdown, PDF and Word. `docs/assessments/2026-10-26-doc-artifact.md` has the
design and six steps; decision 0025 (proposed) records the choice and freezes the Word panel.

Facts checked in the code: a deck's comments are kept in `comments.json` beside it (0015); the
Design artifact exports PDF through the browser's print dialog; `markdown-it-py` gives each block's
line range; `write_docx` and `add_docx_chart` cover the Word export; the desktop app has no
`printToPDF` today.

Not verified: that Tiptap's markdown extension can serialize one block (step 1 checks); that models
choose a Doc and write the two additions unprompted (step 6 measures it).
