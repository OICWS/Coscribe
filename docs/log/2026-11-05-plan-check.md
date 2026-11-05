# A turn that stops with its plan open goes on once, and a repeated read is noted (shipped)

Why: step 2 of #819. In the live tests, the model sometimes ended a turn with tasks of its own plan still open, so the user had to say "you didn't finish". After its context was cleared or compacted, it also read the same file again.

## Shipped
- The plan check (`runtime_lg/turn_checks.py`):
  - It applies when the model ends a turn that created or updated tasks while some are still open.
  - The open tasks are sent back to the model once in that turn, as a marked note.
  - The note isn't counted as a request and isn't shown in the chat history. Edit and rewind skip it.
  - Tasks left over from earlier work don't hold up a turn that didn't touch them.
- If the model replies again without a tool call in between, the second reply starts a new paragraph (`conversation/turn_stream.py`). Before, the two replies ran together.
- The repeat note: a read (filesystem, documents and web tools) made again with the same arguments in the same turn gets a note on its result. It only applies when no call that changes things (a write, a command, a sub-agent) came in between. The call isn't blocked: the file may have changed outside coscribe, or the earlier result may have been cleared from the context.
  - The note runs inside the middleware that catches tool errors, so a sub-agent's sync run gets it too.
- Tests: `tests/test_turn_checks.py`, and two chat tests in `tests/web/test_chat_events.py`.

## Not verified
- A real Windows machine. The measured effect is in the PR, from the multi-turn evaluation (`evals/agentic/`) run with `deepseek:deepseek-flash` against the baseline on `main`.

## Follow-ups
- Steps 3 to 6 of #819 (`docs/plan.md` item 9).
