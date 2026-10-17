# Word review tools: changes and comment threads one by one (shipped)

Why: the Word viewer (decision 0014, `docs/assessments/2026-10-17-file-viewers.md` §3.2-3.3)
acts on a file's review through the backend, and the model gets the same operations. Before
this, tracked changes could only be accepted or rejected all at once (or per author), and
comments could only be written by `write_docx`.

## Shipped
- `tools/office/docx/_review.py`: reads and edits the package's XML parts directly (python-docx
  knows neither single changes nor comment threads).
  - Read: insertions and deletions in document order with id, author, date, text and the heading
    they fall under; a count of other changes (moves, formatting, paragraph marks); comment
    threads with the words they are anchored to, `done` and replies, from
    `commentsExtended.xml`.
  - Edit, all or nothing: accept or reject one change or all, reply, resolve or reopen a thread,
    comment on words that occur exactly once (the runs are split at the words' edges). A reply
    gets its own anchor and reference next to its parent's, as Word writes it.
  - Tools `read_docx_review` (READ) and `edit_docx_review` (WRITE_LOCAL): two deferred tools, so
  the schema snapshot changed (decision 0001). The Word skill names them.
- Tests: `tests/test_docx_review_tool.py` (6). A file with a reply, a resolved thread and a new
  comment round-trips through LibreOffice with the reply threaded under its parent, resolved,
  and the new comment anchored on just its words.

## Not verified
- Opening an edited file in Word on Windows: threads, resolved state and the split runs.
- Files written by Word with `commentsIds.xml` / `people.xml`: they are kept as they are, but no
  real Word file was tried.

## Follow-ups
- The routes: `GET`/`POST /api/threads/{id}/docx-review` and the Original copy (step 2, part 2).
