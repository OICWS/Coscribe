# Stop keeps the reply so far, and a message typed while a card waits answers it (shipped)

Why: the maintainer found Stop clumsy. Pressing Stop threw the reply away: the page showed only
"[stopped]", the history kept only the user's message, and the next turn saw two requests in a
row with no sign the first was stopped, so the model often started the stopped work again.
And text typed while a question or an approval card waited became a note for a turn that was
stuck on that card: the card stayed open and the note was never read.

## Shipped
- A stopped turn keeps the text it had streamed, on the page and in the history, ended by
  "[stopped]". This holds for both kinds of stop: the cooperative one between chunks and the hard
  cancel of a model call in flight (`conversation/stopped_turn.py`, reached through
  `TurnStreamer.stopped` in `conversation/turn_stream.py`).
- The history also gets a hidden note for the next turn (`runtime_lg.stopped_turn_messages`): the
  user stopped the turn, which calls were cut off, that finished steps keep their results and
  are not redone, that the stopped work is not taken up again unless the user asks, and which
  background scripts, commands and sub-agents still run. The note is marked like the plan check,
  so it is not shown in the chat or counted as a request, and it survives a restart because it
  is in the checkpoint.
- The page shows the stop as a quiet "Stopped · What should I do instead?" line under the reply,
  not as "[stopped]" in the prose (`frontend/src/components/chatlog/StoppedNote.tsx`); a turn
  stopped before it said anything shows only that line. Until the turn has ended, the time and
  token line under the message box says "Stopping…", and pressing Stop puts the cursor back in
  the message box. When background tasks are still running after the stop (Stop
  does not end them), the line says how many and opens the Background tasks panel. Copy leaves
  the marker out.
- A question left open by the stop is named in the note, so the next turn doesn't open by asking
  it again.
- Text typed while a question card waits is the answer: the card closes showing it, and the model
  reads "the user didn't pick an option and wrote this instead" (`question_answer`,
  `format_question_answers`). Text typed while an approval card waits denies the call with those
  words, which the model reads and the card shows (`ApprovalDecider`). Both live in
  `frontend/src/lib/steerNotes.ts`, where a note would otherwise have gone.
- A socket that drops keeps nothing (a reconnect resumes the turn), and a conversation being
  deleted is not written back.
- Tests: `tests/test_stopped_turn.py`, `tests/web/test_stop_keeps_work.py`,
  `tests/web/test_chat_card_replies.py`, and `splitStopped` in `chatlog/helpers.test.ts`.
- Checked in the real app with `deepseek-flash`: a stopped essay keeps its text and the next
  message ("just three sentences") is answered without resuming it; a reply typed at an open
  question closes it and the model writes the line in the chat; a reply typed at an approval
  card denies the write and the model asks for `hello.txt` instead.

## Not verified
- A real Windows machine with a real model: whether the model follows the note and answers the
  next message instead of resuming the stopped work.

## Follow-ups
- A denied call still shows a second, red row under its card (the reducer adds its rejection as a
  tool row; `reducer.test.ts` pins that). Folding it into the card needs care so a later call of
  the same tool doesn't land on the old card.
- A script that reaches its time limit, or gets a message mid-turn, moves to the background
  (`docs/plan.md` item 9).
