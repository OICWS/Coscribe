# 0036: A step runs several lanes of steps at the same time

Status: proposed (2026-11-03, kurtosisOC; needs the maintainer's acceptance). Narrows 0035 (a
called task may now run in a lane, beside other work). Builds on 0032, 0033 and 0035. Issue #788,
batch 1.

## Context
A task that gathers from several places (a report site, a folder, a mailbox) went through them
one after another, though none needed the others, and a slow site held up the rest.

## Decision
- **A parallel step** (`kind: "parallel"`) holds 2 to 6 `lanes`, each a label (different from
  the others, ignoring case) and its own steps. All lanes start together; the run goes on once
  every lane has ended. It may say what happens when it fails, like a tool step, and counts
  toward the nesting limit. A new kind changes nothing an older workflow says.
- **A lane reads only what came before the step**, never another lane's results, and lanes
  save different names; after the step, every name a lane saved can be read. Saving checks both.
- **Each lane runs as a run of its own**, as a called task does (0035): on its own checkpoint
  thread in the caller's store, from the caller's values, its records the caller's under their
  own ids. Running a lane as a separate run keeps one pause per graph step, which pausing,
  answering and retrying already rely on; LangGraph's own fan-out would pause several branches
  at once.
- **Pauses are asked one at a time**, once every lane has ended or paused, each keyed by where
  its lane stopped, since LangGraph replays earlier answers when the step runs again.
- **A failed lane lets the others end, then the step fails** naming the lane. A retry, of the
  step or of a step in the lane, goes on in the lanes that failed, from the step that failed (a
  person's no is asked again); finished lanes are not run again, so nothing is sent twice.
- **Lanes that may use the browser take turns**, since there is one: a browser tool, an agent
  that may open sites or go beyond its tools, or a called task.

## Consequences
- The editor, quick edit, canvas, run view, side panel, run report and test runs know the new
  step; the drafter is told when to use it. The compiled graph shows it as one node.
- What a lane reads and saves stays visible in its own steps; the step itself saves nothing.
- Out of scope: a lane that waits for another lane, a limit on how many lanes run at once
  across runs, and lanes over the items of a list (a loop still goes one item at a time).

Retired wording: "Out of scope: running a called task in parallel"
