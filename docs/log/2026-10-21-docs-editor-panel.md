# Docs: the editor in the Word panel (shipped, first version)

Why: decision 0019. A Word file can now be edited in the app, not only viewed and commented on.

## Shipped
- An **Edit** button in the Word panel's header opens the editor; **Word layout** goes back to the
  page view. The editor is Tiptap 3 (MIT) with a schema limited to what the file can hold through it:
  a title, headings 1–3, paragraphs, quotes, bulleted and numbered lists (three levels), tables with
  one paragraph per cell, bold, italic, underline and links (http, https, mailto).
- One row of tools: undo and redo, the paragraph style, bold, italic, underline, lists, quote, link
  (the app's own dialog), and a table menu (insert 3 × 3; add or delete a row or column; delete the table).
- What the editor cannot change (comments, tracked changes, contents, pictures, charts, breaks) is a
  grey locked line that stays as it is and can be deleted.
- Saves happen a moment after typing stops and when the panel closes, through
  `PUT /api/threads/{id}/docs/blocks`. The answer's ids are put on the nodes, through whatever was typed
  meanwhile, so the next save addresses the same blocks. A file changed since it was read is not
  overwritten: the panel says so and offers Reload. When coscribe changes the file in a turn and nothing
  is waiting to be saved, the editor reads it again.
- The editor and its library are a separate chunk (about 460 kB, 145 kB gzipped), loaded when a
  document is first edited; the main bundle is unchanged.
- Tests: the conversion between blocks and the editor's document (nesting, ids, marks, header rows),
  and two Playwright specs against the real server: typing, a new heading and a list reach the file,
  the comment and tracked changes are still there, the Word layout shows the result, and a stale save is refused.

## Not verified
- Typing Chinese with an input method in the packaged app; paste from Word or a web page (not cleaned yet).
- The file opened in real Word on Windows after an edit.
- Undo does not cover coscribe's turns yet, and coscribe is not told what the person edited; both are the next step,
  with the selection bubble, the slash menu, images, a divider and a page break.
