# A scheduled task's page opens on a simple view (shipped)

Why: the maintainer found a task's page too technical for an ordinary user. It opened on a node
diagram labelled TOOL and SCRIPT with variable names, tool names and code, then five autonomy chips,
a bare environment name and a permissions box of caveats, with the runs last (#773).

## Shipped
- `frontend/src/components/ScheduledTaskSimple.tsx`: the simple view of a workflow task, the
  default. In order:
  - what it does, as the workflow's canvas in plain words;
  - what it asks for at each run, by label and usual value;
  - the five most recent runs;
  - when it runs, with Change;
  - if a step stops working;
  - what it may touch.
- `components/workflow/WorkflowCanvas.tsx`: a `plain` form of the canvas, the same layout
  (branches side by side as "If so" and "If not", loops in a frame) with plain cards:
  - A card shows a category in its own colour (Website, File, Program, AI, Check, Your OK,
    Choice, Repeat), the step's title and one sentence from `lib/plainSteps.ts`. For example:
    "Types the claim's name into 'Full name'".
  - No card shows a tool name, a variable name, code or a step number. A value from an earlier
    step reads "the claim's name", and an input reads its label.
  - A step that can't be undone is tagged.
  - A loop names itself on its frame. A loop of more than 5 steps shows its first 3 and a button
    that counts the rest and how many of them can't be undone.
  - Clicking a card opens that step in the Detailed view's editor.
  - Two colour tokens are new: `--kind-web` and `--kind-file`.
- `AutonomySetting.tsx`: `AutonomyChoice`, the task's autonomy as one select in plain words. It
  shows the level a task without the setting acts at (`neededAutonomy` in `lib/workflowLabels.ts`,
  mirroring `workflow_spec`), and levels below what the steps need can't be picked.
- `WorkflowPermissions.tsx`: a `simple` form, with one line per kind of reach.
- `ScheduledTaskDetail.tsx`: a Simple / Detailed switch, remembered in this browser
  (`lib/taskView.ts`). Detailed is the page as it was. A run's "Edit step" opens Detailed. The
  status row and the detailed body are their own components.
- `ScheduledTaskModal.tsx`: the environment box says "Runs in the environment".
- Instruction tasks (no workflow) keep their one page.

## Not verified
- On Windows, in the desktop app. Checked in Chromium against a live server, on three saved
  tasks: a browser task with a loop, a script task and a task with a branch.
- The dark theme's colours for the two new tokens (picked, not looked at).

## Follow-ups
- Change a task by describing the change in words (in `docs/plan.md`).
