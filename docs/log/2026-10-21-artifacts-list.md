# Artifacts, part 1: the list of what the conversations made (shipped, nothing shows it yet)

Why: the maintainer wants an Artifacts page that lists what coscribe has made (issue 497). The page
comes in the next change; this is the list it reads.

## Shipped
- `GET /api/artifacts` lists the decks (.pptx), documents (.docx) and spreadsheets (.xlsx) the
  conversations made or changed, newest first: kind (slides, docs, sheets), name, path, the
  conversation, when the file last changed and, for a document, its heading and opening lines.
- It is derived from each conversation's Outputs (the files its tool calls wrote, as the side panel
  lists them), read from the checkpoints without opening a session; a conversation is read again
  only when it has a newer checkpoint, and every file is looked at fresh, so a deck edited in the
  Slides panel shows its new time. A file two conversations touched is listed once, under the one
  that made it. Scheduled runs are not listed yet.

## Not verified
- Not run against a real workspace or the app; the route is covered with a stub model.
