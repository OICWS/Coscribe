# A comment card closes on a click outside it or Escape

Why: a comment card, once opened (new or an existing thread), could only be closed by posting,
resolving or deleting; clicking elsewhere left it open.

## Shipped
- `components/slides/SlideComments.tsx`: the card's popover closes on a pointer press outside it
  and on Escape. A press on another pin closes this card and opens that one.

## Not verified
- Not run in a browser here; the frontend build passes.

## Follow-ups
- none
