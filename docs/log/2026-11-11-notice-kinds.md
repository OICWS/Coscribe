# Notices above the message box show what the conversation made, each kind its own way (shipped)

Why: the notice stack above the message box held only workflow drafts and the
save offer. The maintainer asked for a notice per kind of thing the assistant
makes, modelled on a list of PR and document cards, and agreed the designs on
screenshots first.

## Shipped
- What the conversation made comes from `GET /api/threads/{id}/activity`
  (its outputs), fetched again after each finished call
  (`components/outputNotices.tsx`, sorting in `lib/madeOutputs.ts`).
- A document, deck or design: its kind's icon and colour, its name in the body
  font, then "Presentation · updated 2m ago". The row opens it in its panel. A
  design's pages are the one design; a Markdown file counts only when the server
  reads it as a Doc.
- Pictures: one notice with up to three thumbnails. The row or View all opens
  a viewer with arrows, a strip and Copy (`components/ImageGallery.tsx`); one
  picture gets Copy on the row.
- Excel, Word, PDF, CSV and old PowerPoint files: the name in mono, the type
  and folder, Open (its own program) and a folder button (Show in folder).
- A call waiting for approval, or a plan waiting for an answer, gets a notice
  while its card is scrolled out of sight; Show scrolls back to it
  (`components/waitingNotice.tsx`). A question has no notice: its panel already
  sits above the message box.
- A closed notice stays closed until its file changes again (kept in
  localStorage per conversation, file and modified time).
- `copyImage` moved to `lib/copyImage.ts`, shared with the attachment menu.

Checked against the dev server with the stub model: the outputs route mocked in
Playwright with real pictures in the workspace, light and dark, a narrow chat
beside the Design panel, the picture viewer, and a write_file approval scrolled
out of view and back.

## Not verified
- On Windows: Open and Show in folder starting Excel and Explorer, Copy putting
  a picture on the clipboard in Electron.
- Against a real model's turns.

## Follow-ups
- The model has no tool that saves a browser screenshot as a file, so a page
  it looked at doesn't show as a picture notice.
