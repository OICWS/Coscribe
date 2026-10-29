# Decision 0028 proposed: a workflow step chooses its autonomy (partly shipped)

Why: a scheduled task is either fixed steps with no agent at run time or written instructions an
agent works out every run, with nothing between. A mostly fixed workflow that hands an
unexpected case to an agent, and then hardens that case into a fixed branch, is the direction
(#719).

## Shipped
- `docs/decisions/0028-a-workflow-step-chooses-its-autonomy.md` (proposed), superseding 0005 in
  part (0005 marked to match); the decisions README gains 0026 to 0028.
- `ARCHITECTURE.md`, "Repeated work becomes fixed steps": the section rewritten around autonomy
  per step.
- `docs/plan.md`: item 8, the phases P0 to P5.

## Not verified
- Nothing to run: documents only. The record needs the maintainer's acceptance before P1.

## Follow-ups
- P1 to P5 in `docs/plan.md` item 8.
