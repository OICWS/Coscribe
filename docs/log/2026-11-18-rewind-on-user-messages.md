# Rewind and Edit sit on each sent message, with its time (shipped)

Why: Rewind and Retry were at the bottom of the last reply only, and Edit only worked on the most
recent message. A stopped turn also ended in a square icon and "Stopped", which read as noise.

## Shipped
- Hovering a sent message shows when it was sent ("2 hours ago", the full time on hover), Rewind
  to here, Edit and Copy (`frontend/src/components/chatlog/SentMessageActions.tsx`). Both work on
  any message after the last /compact: Rewind takes it and every later turn out and puts its text
  back in the message box; Edit (Cancel / Save, Save once the text changed) does the same and
  sends the new text as the latest message.
- When a turn being removed wrote a file, ran a command or acted on a connector, the Rewind and
  Edit tooltips (and the edit box's info icon) add that those changes stay; Rewind still acts on
  one click (`frontend/src/lib/messageActions.ts`, matched by the call's verb).
- Disabled, with the reason, while a reply runs or an approval, question or plan waits (the server
  refuses both then).
- The server keeps each user message's send time (`sent_at`, in the message's
  `additional_kwargs`, never sent to a provider) and replays it (`UserEntry.sent_at`); messages
  from before this have no time. `edit_message` accepts any visible message, not only the last.
- The reply's footer keeps Copy and when the reply finished; Retry is gone (Edit with the text
  changed does it).
- A stopped turn shows nothing extra, unless the stop left background tasks running.
- Tested live with DeepSeek (deepseek-flash): `tests/e2e/message-actions.spec.ts` passes (rewind
  and edit of an earlier message, both checked after a reload).

## Not verified
- On Windows in the desktop app.

## Follow-ups
- A reply's finish time is known only in the tab that watched it; after a reload the footer shows
  Copy alone. Keeping it needs a time on the AI message (see `docs/plan.md`).
