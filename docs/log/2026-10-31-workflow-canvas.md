# A workflow's page opens on a read-only canvas of it (P2b of #719; shipped)

Why: a workflow was shown only as the editor's list of cards, which is the
right place to change a step but a poor one to see the whole: what runs in
what order, which way a branch goes, what repeats, where an agent works or a
person is asked.

## Shipped
- `WorkflowCanvas.tsx`: the workflow from Start (with its inputs) to Done.
  - Each step is a card with its kind (an agent's level too), number, title and summary.
  - A branch splits into its two arms side by side and joins again.
  - A loop's steps sit in a dashed frame.
- The layout follows the workflow's structure, so it needs no graph library and keeps the
  order the engine runs. It is read-only: clicking a step opens it in the editor.
- `WorkflowSection.tsx`: a task's page and a draft's page show "Overview" (the canvas, the
  default) or "Edit steps" (the editor). A run's "Edit step" opens the editor on that step.
- React Flow with an ELK layout was considered and not needed: the structure is a tree, not a
  graph, and drawing it from that adds no dependency.
- An agent step's summary says its reach ("2 tools", "Any tool", "The whole task") and its
  fields after "returns"; the "Agent" kind is on its tile and the canvas card.
- Tests: `tests/e2e/workflow-canvas.spec.ts` (loop frame, both arms, Done, a click opens the
  step in the editor), added to the e2e job's list.

## Not verified
- On Windows and in the desktop app (checked in Chromium, light and dark).
- A very wide workflow (many nested branches): the canvas scrolls sideways; there is no zoom.

## Follow-ups
- The run's step statuses on the canvas, so a run can be watched on it.
