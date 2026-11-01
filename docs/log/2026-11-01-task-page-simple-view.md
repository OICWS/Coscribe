# A scheduled task's page opens on a simple view (shipped)

Why: the maintainer found a task's page too technical for an ordinary user. It opened on a node
diagram labelled TOOL and SCRIPT with variable names, tool names and code, then five autonomy chips,
a bare environment name and a permissions box of caveats, with the runs last (#773).

## Shipped
- `frontend/src/components/ScheduledTaskSimple.tsx`: the simple view of a workflow task, the
  default. In order:
  - what it does, as the steps' titles;
  - what it asks for at each run, by label and usual value;
  - the five most recent runs;
  - when it runs, with Change;
  - if a step stops working;
  - what it may touch.
- `components/workflow/StepOutline.tsx`: the steps as a numbered list. Loops and branches indent
  what they hold. Tags say what a person needs: AI, Check, Waits for your OK, Can't be undone. A
  long loop body shows its first steps, and the "more" button counts hidden steps that can't be
  undone.
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
- On Windows, in the desktop app. Checked in Chromium against a live server, on two saved tasks:
  a browser task with a loop and a script task.

## Follow-ups
- Change a task by describing the change in words (in `docs/plan.md`).
