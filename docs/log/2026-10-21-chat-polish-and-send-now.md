# Chat polish: Send now, open a deck from the conversation, plain startup spinner (shipped)

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
- A deck or document a run of calls wrote or changed shows a chip under the run (its file name);
  clicking it opens the file in its panel, as the Outputs list does.
- The startup splash is only the spinner (no "Starting coscribe" or "Still starting up"; the
  desktop shell's page still says so when the server fails to start), and the desktop page's spinner
  uses the app's blue instead of its old pink, so the hand-off no longer changes colour.
- The properties panel of a selected object no longer has the extra gap above its first section.
- Discard my edits asks through the app's own confirm dialog, not the browser's.

## Not verified
- Send now against a real model mid-reply (the stub model answers too fast to be caught in flight);
  covered: the server drops a withdrawn note before the model reads it (`tests/web/test_chat.py`).
- Not run in the packaged app.
