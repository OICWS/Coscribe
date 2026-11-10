# A record of how each turn went, kept on the machine (partly shipped)

Why: when a turn goes wrong, nothing said how it went: model calls, failed tools, tokens, how it
ended. Only the evaluation had those numbers, for its own runs. Issue #867, decision
[0045](../decisions/0045-how-each-turn-went-is-kept-on-the-machine-without-its-words.md); row 3 of
the engineering assessment of 2026-11-09.

## Shipped
- `conversation/turn_record.py`: `TurnRecorder` counts a turn as it runs, from the run's own
  stream of events, and writes one JSON line per turn to `turns.jsonl` in the state directory: model, effort, mode, seconds, outcome,
  model calls, input / cached / output tokens, calls and errors per tool, and the first 300
  characters of at most 20 tool errors, redacted. No message text, tool arguments or results.
- The file is put aside at about 5 MB (`turns.1.jsonl`) and a new one started.
- Wired where a turn runs (`recorded_turn` on the session's turn method, `observed` around the
  stream in `turn_stream.py`): a typed message, an edited message, and a sub-agent's or
  background task's report (marked `notice`). A command that runs no model (`/plan`) leaves no
  line. `session.py` is one line shorter than before, and the ratchet baseline is lowered to match.
- 15 tests (`tests/test_turn_trace.py`, `tests/web/test_chat_trace.py`).

## Not verified
- A real provider's usage numbers: the tests use a scripted model that reports none, so the
  token sums are tested only on the recorder itself. Tokens are summed from the streamed
  pieces, which is how the app's own counter reads them; a provider that repeats the total on
  every piece would be counted too high.
- Windows: the rename of a full file while another process holds it open.

## Follow-ups
- The model calls of a sub-agent and of a workflow's agent step are not counted.
- The evaluation's replay layer in the PR checks, and a failed turn exported as an evaluation
  task with the person's consent (#867, later parts).
- Nothing reads the record yet: a script that ranks tools by failures is the first reader.
