# 0052: A failed turn leaves the machine only as a file the person saves

Status: proposed (2026-11-18, OICWS).
Issue #867. Adds to 0045, which said a turn's record may leave the machine only with the person's
consent for that one turn and a record of its own: this is that record. 0045 is not changed.

## Context
The evaluation's tasks are written by hand from what the maintainer guesses goes wrong. The turns
that really went wrong are on the machines of the people who use coscribe, in `turns.jsonl`, and
nothing carries one to the person who could make it a task.

## Decision
- **The person starts it, for one turn.** A conversation's menu has "Export a failed turn…",
  listing that conversation's turns that ended on an error, were stopped or had a tool fail
  (`conversation/turn_export.py`). They pick one, see the whole file, and press Save.
- **Saving is the consent, and the file is all that leaves.** The app sends nothing anywhere: the
  file goes where the person saves it, and they choose who gets it.
- **It holds the turn's numbers, named field by field**: when it started, its kind, model, effort,
  mode, seconds, outcome and exception type, model calls, tokens, and calls and errors per tool.
  A field the record gains later stays on the machine until it is added to that list. The
  conversation's id is left out.
- **No words of the conversation.** The start of each tool error goes, as 0045 keeps it, with
  the home folder written as `~`. The person may write, in their own words, what they asked for and
  what went wrong; both are cut at 2,000 characters and passed through `redact_secrets`.
- **The evaluation reads it** with `python -m evals.agentic.candidate FILE`, which prints an
  `AgenticTask` to finish by hand: the file has no files and no messages, so the setup and the
  checks are written before the task runs.

## Consequences
- A failed turn is not a task by itself: without the person's own words, the maintainer writes
  the turns too. The file says which tool failed and how, which is what a task is built around.
- An error text can still name a file inside the home folder, or a folder outside it. The person
  sees it before saving, and the dialog shows the whole file.
- Anything that would send a turn's record somewhere by itself (an upload, a report button) still
  needs its own record.
