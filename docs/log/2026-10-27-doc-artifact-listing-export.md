# Doc artifact, step 5 part 1: the listing, the side folder and the Word export

Date: 2026-10-27
Area: server, tools

A Markdown file is an artifact of kind "docs" when its front matter marks it a Doc (`describe_artifact`
reads it through `read_doc_file`; a plain `.md` is still no artifact), listed with its title and its
first paragraphs as the excerpt. The artifact menu now moves the Doc's side folder with it: a rename
renames `name.doc/` too (and refuses when that name is taken), a copy starts with the pictures but
not the comments or the kept versions, and the recycle bin takes the folder with the file.

`POST /api/threads/{id}/doc/export` returns the Doc as a Word file made for the download and kept
nowhere (`docx_markdown`, then `docx_from_markdown` in the house style). What the writer's subset cannot
hold is written as the nearest thing: a callout as a bold label and its text, a chart as its title and its
table, a picture as `[Picture: alt]`, raw html as nothing. Markdown and PDF are made in the browser.

Not verified: the export opened in the real Word on Windows; a chart as a native Word chart (it is a
table in the export); a Doc moved by hand in the file manager loses nothing but must take its folder.
