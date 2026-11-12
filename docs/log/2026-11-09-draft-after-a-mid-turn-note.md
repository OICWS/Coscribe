# A workflow can be drafted in a conversation where the person wrote mid-turn (shipped)

Why: the maintainer reported that `draft_workflow` and `revise_workflow` both failed every time
with the error `'arguments'`, even after a restart, so a tested browser job couldn't become a
fixed workflow and the first draft's card stayed. A note sent while a turn runs (a steer) is
replayed as its own entry kind, and the transcript the drafter reads took every entry that wasn't
a user or assistant message for a tool call.

## Shipped
- `render_conversation` (`workflows/solidify.py`) reads a steer as the person's words and skips
  any other entry kind it doesn't know.
- Test: `test_a_note_written_while_a_turn_ran_reads_as_the_persons` (fails on main with
  `KeyError: 'arguments'`).

## Not verified
- On the maintainer's conversation itself (Windows); the cause was reproduced from the error.
