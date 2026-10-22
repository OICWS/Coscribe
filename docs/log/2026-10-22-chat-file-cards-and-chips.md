# Chat: a card at the end of a turn and a chip in the text for the files it made (shipped)

Why: the maintainer's reference (Claude) points at a made document twice: a chip with a hover card where
the reply names it, and a card at the end of the answer. The chat had only a small "Open" button, and
none at all for a file whose write had been approved.

## Shipped
- **End card**: the decks and documents a turn made or changed are listed as cards after its answer: a
  tile in the kind's colour, the name, "Document · .docx" (or Presentation), an arrow; a click opens the
  file in its panel. It replaces the small "Open" buttons.
- **Chip in the text**: when a reply names a file this conversation made or changed (in running text or in
  backticks), the name is drawn as a chip with the kind's icon; a click opens the file, and hovering
  shows a card: its kind, its name, and when it last changed. A name inside a longer word or path, in a
  link, or in a code block is left as text, and a file the conversation did not make is not guessed at.
  The chip is a remark plugin over the reply's own Markdown (`lib/fileMentions.ts`); no reply text or
  prompt changes.
- **Fixed on the way**: a write the person approved is an "approval" item carrying its result, which the
  old buttons ignored, so such a file never got a button. Both now count it.
- The stub model (`scripts/stub_llm.py`) can answer with chosen words (`[[stub-say TEXT]]`), so a spec
  can have a reply name a file.
- Tests: vitest for what counts as a made file and for the plugin (running text, backticks, look-alikes,
  links, code); a Playwright spec: the stub writes a document and names it, the chip and its hover card
  and the end card are checked, and the card opens the panel.

## Not verified
- The hover card with a Chinese file name or a very long one; a reply naming two files with one name
  (the later path wins).
- A file written by a script (not by a document tool) is not known to the chat, so it gets neither.
- The packaged app on Windows.

## Follow-ups
- Spreadsheets: the cards and chips are for decks and documents, the files the viewer shows.
