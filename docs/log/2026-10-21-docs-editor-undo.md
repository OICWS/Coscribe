# Docs editor: undo of a change made behind it (shipped)

Why: when coscribe (or Word) changed the document while it was open, the editor read the new file and
its own undo, which holds only the person's typing, could not take that change back.

## Shipped
- The server keeps the versions of a document the editor has held (`state_dir/docs_history/`, up to 20,
  files over 25 MB not kept): a version is kept when the editor reads it and when it saves. The person's
  saves while they type are one step, ended by something else changing the file; the editor's own undo
  still takes typing back letter by letter.
- When the editor reads a file that changed behind it, a line over the document says so, with **Undo**. Undo
  puts the version the editor held back as the file (`POST /api/threads/{id}/docs/restore`, over the
  version the editor holds, refused with a 409 if the file moved on); the line then offers **Redo**, which
  puts the change back. Typing in the document ends the offer: taking it back would take the typing too.
- A version asked for that is no longer kept, or a name that is not a version, is refused; the line says
  so.
- Tests: the kept versions (one step, the cap, the size limit), the restore (back, forward, refused over a
  newer file, a version gone, a bad name), the route, and a Playwright spec: a change made behind the
  editor, the line, Undo, Redo, each checked in the file.

## Not verified
- With a real coscribe turn that rewrites a document (the spec changes the file through the editor's own
  route, which is the same to the editor).
- A change made while the editor was closed is not offered: nothing was held to go back to.
- The packaged app on Windows.

## Follow-ups
- Version history as a list to browse and restore from (wanted, not in v1): in `docs/plan.md`.
