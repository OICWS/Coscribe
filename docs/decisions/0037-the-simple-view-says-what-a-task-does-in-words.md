# 0037: The simple view says what a task does in words

Status: proposed (2026-11-07, kurtosisOC; agreed with the maintainer in the project thread).
Issue #833.

## Context
Most people who use a task never read how it is configured. The simple view showed what a task
does as a flowchart, its AI steps all said "AI reads what came before and writes the result",
and its settings sat in the middle of the page beside what it does.

## Decision
- **One sentence on top** says what the task does. A model writes it, not a rule: the side
  model (`side_model_name`, the same as a conversation's title) from the task's name, inputs
  and step titles, once per saved version, kept beside the versions
  (`task_versions/<id>.overview.json`), so opening the page again makes no call. A sentence the
  person wrote is kept whatever the version; clearing it lets the model write one again. No
  sentence (no model, a failed call) is not an error: the page shows none.
- **What it does** is a numbered list of plain sentences, a block's steps under the words that
  say when they run (a lane by its name, "Otherwise", "For each ..."); an input a step reads is a
  chip. The flowchart is behind "Show the flowchart".
- **What it needs from you** gathers what the person fills in, where a run waits for them and
  what it may touch, including a page whose address is filled in as it runs.
- **Settings** (when it runs, if a step stops working, where it runs, versions) are folded under
  one line that sums them up.

## Consequences
- Every control still changes the same settings the detailed view shows; the detailed view and
  the editor do not change.
- A new version costs one short side-model call the first time its page is opened.
- Next: the run page (the result first, then the steps as a checklist, the raw output behind
  Details).
