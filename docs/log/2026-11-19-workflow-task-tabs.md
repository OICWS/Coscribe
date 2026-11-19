# A workflow task's page in one row of tabs; notices above the message box react to hover (shipped)

Why: the maintainer found the workflow task page confusing (a Simple / Detailed switch with four
more views inside Detailed, the same settings twice in different words), and a made file's
notice opened only from its text with nothing on hover to say it could.

## Shipped
- `components/ScheduledTaskDetail.tsx`: tabs Overview, Steps (with counts), Runs, Settings under
  the header; the page switch and the header's "Workflow · 7 steps" are gone (decision 0053).
- `ScheduledTaskSimple.tsx` is the Overview: four tiles (when it runs, last run, if a step stops
  working, workspace), each opening the tab that changes it, in place of the folded Settings.
- `workflow/TaskSettingsTab.tsx`: every setting once, in four cards; the webhook address moved
  here from the runs list. The plain autonomy dropdown is gone; the radio levels stay.
- `workflow/QuickEditPanel.tsx`: "Change this step" and "Change what it asks for" are a floating
  card like the dock's panels (rounded, header with expand to the full editor and close), with no
  grey backdrop; the task page makes room for it, Escape closes it, and another step can be
  picked while it is open.
- `NoticeStack.tsx`: a notice that opens something is clickable on its whole row, shows a
  pointer and a darker background on hover, and a ring when its button has keyboard focus.
- e2e specs that opened Detailed now open the tab; the 12 workflow, task-reach, permissions and
  notice specs touched pass locally on the stub model, except the connector one below.

## Not verified
- The desktop app on Windows.
- `workflow-connector-trigger.spec.ts` fails here before and after (its fake connector is not
  set up in this container); CI's nightly e2e run covers it.
