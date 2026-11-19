# 0054: A workflow task's page is one row of tabs

Status: proposed (2026-11-19, OICWS). Narrows 0037: its simple view is now the page's Overview tab.

## Context
A workflow task's page had two levels of views: a Simple / Detailed switch for the page, and
inside Detailed four more (Overview, Edit steps, Settings, Runs). The same setting showed twice
in different words (Autonomy against "If a step stops working", Repeats against "When it
runs"), the flowchart sat in three places, and four controls opened some kind of edit. People
using a task could not tell where to look.

## Decision
- One row of tabs under the header: **Overview**, **Steps**, **Runs**, **Settings**. No page
  switch; the run page keeps its own Simple / Detailed (0038).
- **Overview** is what 0037 called the simple view: the sentence, then one tile per setting
  (when it runs, last run, if a step stops working, workspace) that opens the tab changing it,
  the steps by their titles (the sentence 0037 put under each mostly repeated the title, so only a
  screen reader reads it, and the step's card shows it), what it needs from you, and the latest
  runs with what it keeps between runs.
- **Steps** is the editor, with the flowchart as its second view; a step clicked on the chart
  opens in the list. The chart, here and on the Overview, names each step by its kind and title
  only: the people who read it change a task by asking AI, not by reading tool arguments. A run's "Edit step" and an overview step's "open in the editor" land here.
- **Runs** lists every run. **Settings** holds each setting once, in four groups: when it runs
  (with a program's webhook address), if a step stops working (the autonomy levels and looking
  into failures), where it runs and what it may touch, and versions.

## Consequences
- Every setting has one place to change it; the overview only shows and links.
- A task from instructions rather than steps keeps its single page.

Retired wording: "the task page's simple view", "edits steps in the detailed view"
