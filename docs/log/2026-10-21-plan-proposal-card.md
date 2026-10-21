# The plan proposal card (partly shipped)

Why: #506, PR 2 of 4. The plan the model wrote in plan mode was a card with three long buttons; it now reads like the reference: a row for the source, a card with the choices, the document in the Plan panel.

## Shipped
- `PlanCard`: a "Proposing plan" row that opens the plan's markdown source, and a card "Claude proposed a plan" with Reject, Revise…, Accept, Accept and auto mode and Open plan. Revise… asks "What should change? (optional)" with Back and Revise. Accept keeps plan mode's per-change approvals, Accept and auto mode switches to auto mode (the two answers the card had before). Open plan opens the Plan panel.
- Reject ends the planning: a new answer `reject` of `exit_plan_mode` (`PLAN_CHOICE_REJECT`) gives the model "The user rejected the plan" and nothing to carry out; plan mode stays read-only. A reloaded conversation shows the same outcome (`planStatusOf`).
- Unit test for the new answer (`test_approval_decisions.py`, `reducer.test.ts`) and `plan-proposal.spec.ts` against the stub model.

## Not verified
- Not run on Windows or in the desktop shell.
- The Plan panel does not open by itself when a plan arrives; Open plan does it.

## Follow-ups
- #506 PR 3 and 4: the diff of a changed plan, a comment on selected text sent inside Revise.
