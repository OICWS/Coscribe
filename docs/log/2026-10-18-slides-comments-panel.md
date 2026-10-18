# Slides step 3, part 2: comments in the panel, and Send to coscribe

Why: design §5 and mockup 2. Click anything on a slide to comment on it. A comment can go to
coscribe as a message, and coscribe's answer comes back as a reply (issue #420).

## Shipped
- The panel header has the comment button: a speech bubble, and a chevron with Comment on the
  slide and Show resolved comments. Escape leaves comment mode.
- In comment mode the element under the pointer is outlined. The smallest element under the point
  is chosen, so a click in a card picks its words, and hairlines are easy to hit.
- A click opens the comment card, as in the mockup:
  - the place ("Slide 2 › Title "…"");
  - the @coscribe chip;
  - Send to coscribe, ticked by default;
  - post on Enter.
- A comment's marker is its author's initial on the point. A click opens its thread: replies,
  reply, resolve or reopen, delete. A sent comment says its answer will appear there.
- The card sits beside the point on whichever side has room, kept inside the window, so a narrow
  panel never cuts it off.
- Send to coscribe sends a message to the conversation. The message names the deck, the slide,
  the element and the page file, and quotes the comment.
  - When that turn ends, coscribe's last words in it are posted as the comment's reply
    (`lib/commentReplies.ts`).
  - The panel polls every 5 s while a sent comment waits for its answer. That covers a panel in
    a window of its own, where the turn runs in the main window.
- `App.tsx` gains three lines; two WHAT-only doc comments there were cut to their WHY, so it
  stays at its ratchet.
- Tests: `src/lib/slideComments.test.ts` (which element a point picks, the message) and
  `src/lib/commentReplies.test.ts` (which text is the answer, waiting for a queued message).

## Checked
- In Chromium against a live server with the stub model, in the real app: open the Q3 deck from
  Task details, comment on slide 1 with Send to coscribe, the turn answers "OK", and "OK" appears
  in the thread as coscribe's reply.
- In the narrow panel the card flips to the left of the point.

## Not verified
- The panel in a window of its own on Windows: its Send goes through the panel window's action to
  the main window, which the browser run did not exercise.
