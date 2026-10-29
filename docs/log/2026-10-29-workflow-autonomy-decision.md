# Decision 0028 proposed: a workflow step chooses its autonomy (partly shipped)

Why: a scheduled task is either fixed steps with no agent at run time or written instructions an
agent works out every run, with nothing between. A mostly fixed workflow that hands an
unexpected case to an agent, and then hardens that case into a fixed branch, is the direction
(#719).

## Shipped
- `docs/decisions/0028-a-workflow-step-chooses-its-autonomy.md` (proposed), listed in the
  decisions README.
- `ARCHITECTURE.md`, "Repeated work becomes fixed steps": a paragraph on the proposal.
- `docs/plan.md`: item 6, the phases P0 to P5.

## Not verified
- Nothing to run: documents only. The record needs the maintainer's acceptance before P1.

## Follow-ups
- P1 to P5 in `docs/plan.md` item 6.
