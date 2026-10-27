# Doc artifact, step 2: reading and saving a Doc, kept versions, what the person changed

Date: 2026-10-27
Area: tools, server

Step 2 of decision 0025, as the Word editor's routes are for a .docx (0019). `GET` and `PUT
/api/threads/{id}/doc/blocks` read a Doc as blocks with the version of the file and save the edits
the editor sends (replace, insert, delete, each by block index with the text the editor read); a
save over a file that changed since it was read is `409` with a re-read, an edit that cannot apply is
`400` with nothing written, a markdown file without the marker or not text is `404` or `422` with a
fixed text. `POST /doc/restore` puts a kept version back, so a change made behind the editor can be
undone and done again. Versions are kept in the Doc's side folder (`name.doc/versions`, twenty at
most, the person's saves are one step). The first save since coscribe was told remembers the blocks
before it; the start of coscribe's next turn compares them and says once what the person changed,
in the same line a Word edit uses (`conversation/docs_edits.py` now also looks at `.md` files).

Found by a test: the route first caught the Word editor's `BlocksRefused`, which `coscribe.tools`
also exports, so a bad edit was a 422; the Doc's own is exported as `DocBlocksRefused`.

Left for later steps: pictures (where they are stored and how large they may be) go with the editor
in step 4, because the editor is what adds one.

Not verified: a Doc open in the editor while coscribe rewrites it with the file tools (the save is
refused and the editor reads again, as a unit test shows; the editor does not exist yet).
