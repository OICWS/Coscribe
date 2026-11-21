# A lone emoji the model writes as its reply shows as a reaction (shipped)

Why: issue #1001. After "No thanks" the model sometimes wrote 👍 as its whole reply instead of
calling `react_to_message`, so it showed as a reply on a line of its own.

## Shipped
- `takeReaction` in `frontend/src/lib/reactions.ts`: when a turn on a plain user message holds
  nothing but lone-emoji replies (and reaction calls), the emoji shows as the reaction on that
  message and the reply is not drawn; an emoji written beside the call is dropped. One emoji is one
  grapheme with a pictograph (`isLoneEmoji`, `Intl.Segmenter`), so ❤️, 👍🏽 and 👨‍👩‍👧 count and
  "OK 👍" or 👍👍 stay replies. A lone emoji after other work (a question card, a tool) stays a reply.
- Works on saved conversations too, since it is decided when the turn is drawn.

## Not verified
- Not run against a live model or on Windows; the model writing the emoji as text could not be
  produced on demand. Covered by `reactions.test.ts`.
