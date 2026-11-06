# Stop keeps the reply so far and tells the next turn it was stopped (shipped)

Why: the maintainer found Stop clumsy. Pressing Stop threw the reply away: the page showed only
"[stopped]", the history kept only the user's message, and the next turn saw two requests in a
row with no sign the first was stopped, so the model often started the stopped work again.

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
- The page adds a line when background tasks are still running after the stop, since Stop does
  not end them.
- A socket that drops keeps nothing (a reconnect resumes the turn), and a conversation being
  deleted is not written back.
- Tests: `tests/test_stopped_turn.py` and `tests/web/test_stop_keeps_work.py`.

## Not verified
- A real Windows machine with a real model: whether the model follows the note and answers the
  next message instead of resuming the stopped work.

## Follow-ups
- A script that reaches its time limit, or gets a message mid-turn, moves to the background
  (`docs/plan.md` item 9).
