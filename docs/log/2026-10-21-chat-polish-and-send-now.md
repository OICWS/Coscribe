# Chat polish: Send now for a note sent mid-reply, slash menu width, white approval card, faster context window (shipped)

Why: the maintainer's testing of the packaged app.

## Shipped
- A note sent while the reply is being worked on shows two buttons, Cancel and Send now. Cancel takes
  the note back (the server drops it; its text returns to the composer). Send now stops the reply
  and sends the unread notes as the next message once it has ended. The steer message's text may be
  null for the take-back, so the wire has no new message type; the logic moved from `App.tsx` into
  `lib/steerNotes.ts`.
- The command menu is as wide as the composer box.
- The approval card is white (`--bg`) like the other cards, not gray.
- The Context window popover shows the last breakdown it read for the thread at once and swaps in the
  fresh one, instead of "Loading..." each time.
- Discard my edits asks through the app's own confirm dialog, not the browser's.

## Not verified
- Send now against a real model mid-reply (the stub model answers too fast to be caught in flight);
  covered: the server drops a withdrawn note before the model reads it (`tests/web/test_chat.py`).
- Not run in the packaged app.
