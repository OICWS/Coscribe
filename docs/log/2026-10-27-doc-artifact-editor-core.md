# Doc artifact, step 4a: the editor

Date: 2026-10-27
Area: frontend

Step 4 of decision 0025, first half. `components/doc/DocPanel` opens a `.md` file in the viewer
panel and reads it with `GET /doc/blocks`; the editor is Tiptap over the blocks, each top-level node
carrying the index of the block it came from. A save (`PUT /doc/blocks`, a moment after the person
stops typing and as the panel closes) names only the blocks that changed: a replace with the text the
editor read, an insert after the block before it, a delete. `lib/docModel.ts` does this (`docEdits`),
with `@tiptap/markdown` turning one block into a node and back. A node that holds the same content as
when it was read is never rewritten, so the file's own spelling (`*` bullets, table padding) stays
byte for byte; a block the editor cannot show yet (callout, chart, raw html) is a raw block that
keeps its text. A save over a newer file (coscribe's turn) is refused with a notice and a Reload; a
change made behind the editor's back is offered as Undo, as in the Word editor, through `/doc/restore`.

The look is the reader's: serif or sans for headings and text and the page's width, kept in
`localStorage`, not in the file. Toolbar: undo, redo, font, width, table, checklist and the "+" menu
(lists, headings, quote, code block, divider, table). Selection bar: text style, bold, italic,
strike, code, list, link, and "Ask coscribe" with the three quick requests, sent as a chat message
quoting the words. The title is the first `# ` heading, edited in place.

Not verified: a real Windows machine; the panel opens a `.md` file only through `ViewerPanel`, and no
card, tile or chip sends a file there yet (step 5), so I opened it by a local change to
`isViewable` that is not in this PR. Comments, pictures, callouts and charts are step 4b; a save
over a file coscribe changed meanwhile loses the typing since the last save (a block-level merge
would keep it).
