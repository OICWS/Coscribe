# Artifacts, part 2: the page and the sidebar entry (shipped)

Why: the maintainer's request of 2026-10-21 (issue 497), modelled on Claude's Artifacts page: first
the front end, to settle how it looks and works, then the kinds one by one.

## Shipped
- **Artifacts** under *New session* in the sidebar opens the page (`?view=artifacts`, so reload and
  Back work; `lib/nav.ts`). It lists what `GET /api/artifacts` returns: tabs All and Pinned, a search
  field, a list/grid toggle (the button shows the layout it switches to) and a type filter with a
  count per kind. Docs, Slides, Sheets and Dashboard are the four kinds.
- The grid shows cards: a deck's first slide, a document's heading and opening lines, a stand-in
  drawn in the kind's colour for a spreadsheet, the kind's mark on the card's lower edge, the name,
  "Edited 9m ago" and a pin. The list groups rows under Pinned, Today, Yesterday and the dates.
- "Make something new" shows a tile per kind. Docs, Slides and Sheets start a new conversation with
  the message box begun ("Make a presentation about "); Dashboard is marked Soon and does nothing.
- A card opens the conversation that made it with the file in its panel.
- The card menu has Pin or Unpin (P, which also works as a key while the menu is open); Rename,
  Duplicate, Copy link and Delete are there, marked Soon, until it is decided what they do to the
  files. Pins and the chosen layout are kept in the browser.
- Smaller: `SlideMenu` draws a check mark for the chosen entry, a red entry and a key that picks
  an entry. The window's title bar and page header moved out of `App.tsx` into `AppHeader.tsx`.

## Not verified
- With real artifacts in the packaged app: the page was drawn against sample data in a browser
  (light, dark and narrow) and the sidebar, search, filter, pin, layout and open were run against a
  live server with the list answered by the test.
- A document's or a spreadsheet's card is not a picture of it (a deck's is).
