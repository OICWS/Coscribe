# 0045: How each turn went is kept on the machine, without its words

Status: proposed (2026-11-10, kurtosisOC).
Issue #867. Adds to 0002's audit log, which it does not change.

## Context
When a person says a turn went wrong, nothing on the machine says how it went: how many model
calls it took, which tools failed, what it cost, how it ended. The evaluation writes that for
its own runs (`evals/run.py`); the app writes only the approval decisions (`audit.jsonl`). So
nobody can rank the tools that fail most in real use, or tell whether a change made turns
cheaper or more reliable outside the evaluation, whose 11 tasks all pass.

## Decision
- **Every turn that ran a model or a tool leaves one JSON line** in `turns.jsonl` under the
  state directory (`conversation/turn_record.py`): when it started, the conversation's id, the model,
  effort and mode, whether a person typed it, how long it took, how it ended (completed,
  stopped, error), the model calls, the input, cached and output tokens, and the calls and
  errors of each tool by name.
- **It holds none of the conversation's words**: no message text, no tool arguments, no tool
  results. The one exception is the first 300 characters of a tool's error text, passed through
  `redact_secrets`, for at most 20 errors a turn. A turn that ended on an exception keeps the
  exception's type, not its text.
- **It never leaves the machine.** Nothing uploads it and no route serves it. Anything that
  would send it, or a turn's content, anywhere needs the person's consent for that one turn and
  its own decision record.
- **There is no setting.** The file is cut at about 5 MB, with the file before it kept, so it
  holds the recent turns and does not grow without a limit.
- **Writing it never fails a turn**: a line that cannot be written is lost.

## Consequences
- A turn's line and its approval decisions are joined by conversation id and time; the record
  does not repeat what the audit log holds.
- Deleting a conversation does not remove its lines: they say a turn happened and which tools
  it used, not what it was about. If that is ever too much, the fix is to drop the id.
- Sub-agents' own model calls and a workflow's agent steps are not counted yet; nothing in the
  app reads the file yet; the first reader will be a script that ranks tools by failures.
- An error text can name a file's path. It stays on the machine it came from.
