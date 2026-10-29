# A Markdown file that is not a Doc gets no card (shipped)

Why: while building a deck from pages the agent wrote a `design.md` of notes beside it. The chat
ended with a card for it ("Document · .md") that opened a panel saying "This Markdown file is not a
Doc": a card that leads nowhere. The cards and chips treated every `.md` file as a Doc.

## Shipped
- A card or a chip for a `.md` file shows only when the Doc panel can open it: the same read the panel
  uses (`getDoc`), which answers "not a Doc" for any other Markdown file. Other kinds are unchanged.
  The registry lookup was not used: it fills in as a turn ends, after the card first draws.
- `chat-files.spec.ts`: a plain `.md` written by a turn gets neither card nor chip; a Doc still does.

## Not done
- The Outputs list still lists such a file (it opens in the default app from its row).
