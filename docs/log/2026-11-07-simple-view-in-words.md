# The simple view says what a task does in words (shipped)

Why: most people who use a task never read how it is configured, and the simple view still
opened on a flowchart with its settings in the middle (#833; decision 0037).

## Shipped
- A sentence on top of the page (`TaskOverviewLine.tsx`): `workflows/overview.py` has the side
  model write it from the task's name, inputs and step titles; `POST/PUT
  /api/scheduled-tasks/{id}/overview` writes it once per saved version (a POST, since a first
  look spends a model call) and keeps one the person
  wrote, stored by `TaskVersions` beside the versions.
- What it does as a numbered list (`PlainStepList.tsx`, `lib/plainOutline.ts`): a model step says
  what it works out, a branch its condition, a loop what it goes through, a parallel step its
  lanes by name; an input is a chip, a path or address its file or page. The flowchart is behind
  "Show the flowchart"; a step opens quick edit as before.
- What it needs from you: what the person fills in, where a run waits for them, what it may
  touch (now also a page whose address is filled in as it runs). Settings folded under a line.
- Tests: `tests/test_workflow_overview.py`, `tests/web/test_scheduled_overview.py`,
  `lib/plainOutline.test.ts`.

## Not verified
- The sentence from a real model (here the stub model answered; the screenshots used an example
  sentence written into the store), and the page on a real Windows machine.

## Follow-ups
- The run page in plain words: the result first, the steps as a checklist, the raw output behind
  Details.
