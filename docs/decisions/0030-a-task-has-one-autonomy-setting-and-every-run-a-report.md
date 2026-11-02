# 0030: A task has one autonomy setting, and every run a report

Status: accepted (2026-11-01, by the maintainer; proposed 2026-10-31 by kurtosisOC in #754).
Builds on 0028 (per-step autonomy) and 0029 (irreversible steps). Issue #754. Narrowed by 0032:
a failure stops the run unless the step says to try again, skip it or run other steps.

## Context
0028 lets each step choose its autonomy. A person thinks about a task instead: a finance task
must stay fixed, a report may adapt. Watching every step's level is the detail the person
doesn't want, and a high-autonomy run is only trusted when its result says what it did.

## Decision
- **One switch per workflow, four levels, as a ceiling on its steps.**
  - `fixed`: tool, script, check, approval and `llm` steps only. A failure stops the run, and
    the investigation proposes a revision that the person saves.
  - `self_healing`: the same steps. When a tool step fails because the page or tool changed, a
    bounded agent may reach that step's intent once, within its site. A healed step marked
    irreversible pauses for a person before it acts. Every heal is a deviation in the report,
    and a revision is proposed afterwards.
  - `proactive`: adds `bounded` and `high` agent steps.
  - `autonomous`: adds `full` agent steps.
- **Saving checks the ceiling.** A step above it is refused. Lowering the switch names the steps
  to change. A workflow without the setting acts at the lowest level that covers its steps.
- **Thinking effort stays a separate setting.** The levels may be merged or split by what the
  workflow eval (#754) shows.
- **Every run has a report, read from its step records.** It holds:
  - the rows or items done and not done, and why;
  - deviations from the saved steps (heals);
  - values an agent decided itself (`assumed`, 0028's report);
  - irreversible steps that ran (0029);
  - tool calls, tokens and time.

## Consequences
- The task page shows the switch and the report; the per-step levels stay in the editor.
- Self-healing needs a hook in the engine. `engine.py` is over the size ratchet, so the healer
  lives in its own module, and the engine only calls it.
