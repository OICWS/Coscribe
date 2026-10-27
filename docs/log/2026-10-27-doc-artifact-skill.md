# Doc artifact, step 6 part 1: the Docs skill

Date: 2026-10-27
Area: tools

A built-in skill, "Docs", teaches coscribe to write a Doc (decision 0025): when (documents, reports,
proposals, plans, guides, letters, resumes, manuals; no format named, or only what the person will do
with it; "to send, print or submit" is not a reason for Word, since a Doc exports to Word, PDF and
Markdown), when not (a question or a short summary is an answer in chat; Word, a .docx, a template or
tracked changes is `write_docx` and the Word skill), the file (a `.md` with `coscribe: doc` in its front
matter, blocks separated by blank lines, the callout and chart syntax, a picture copied into
`name.doc/assets/`), how to change one while the person may be editing it (read it again, `edit_file`),
and how comments arrive (a message `Comment on <file>`, answered in chat and written under the comment).
The Word skill's description now says it is for a Word file asked for by name, on a template or with
tracked changes. The "Docs" tile of the Artifacts page asks for a Doc, not a .docx.

No tool changed and the coordinator's instructions are untouched: the skill listing is the only hook, so
whether models choose a Doc without being told is a measurement (next), not an assumption.
`tests/test_doc_skill.py` reads the skill's own callout and chart examples with the app's parsers.

Not verified: that a model loads the skill when it should (measured next, off-peak); the exact wording of
the listing line in a real conversation.
