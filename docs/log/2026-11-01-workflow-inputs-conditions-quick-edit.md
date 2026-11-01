# A workflow asks for typed inputs, goes one of several ways, and is changed from the simple view (shipped)

Why: a monthly task needed "last month" without someone typing it, a branch held only one
condition, a split by department took a branch per value, and the simple view had no way to change
a download address or a loop's limit without the full editor (#776, batch 1; decision 0031).

## Shipped
- `workflow_spec`:
  - `inputs.py`: input kinds text, number, date, choice, yes_no, file, folder. A date may default
    to a relative day (`last_month_start`, `week_start`, ...) worked out when each run starts; a
    run's value is checked against its kind (`input_values`).
  - `refs.py`: comparisons not_contains, starts_with, ends_with, empty, before and after;
    `conditions_hold` reads a list by `match` ("all" or "any") and stops once it is settled.
  - `spec.py`: check, approval `when`, branch and a loop's `until` take a list of conditions and
    `match`; a `choice` step goes one of several paths by a value; a loop may stop early.
    A workflow saved with one `condition` or `when` loads as a one-item list (`current_shape`),
    and the schedule store hands stored workflows out in the current shape.
- `workflows`: the engine wires every path of a branch or choice the same way (`choose_arm`), a
  check with "all" still reports every condition, and a loop that stopped early says so in its
  record. What saving allows never comes from a relative date. The drafter is told the new
  inputs, conditions and steps.
- Frontend:
  - Simple view: clicking a step opens a quick edit (its title, every fixed value, a condition's
    value, each path's value, a loop's limit and stop-early values, and the "can't be undone"
    mark, on only); each input has Change for its name, options and usual value.
  - Canvas: "If" and "Paths" cards; more than three paths stack in a frame that says only one
    runs; cards narrow in a three-way split.
  - Editor: All of these / Any of these, the Paths step, Stop early in a loop, typed input
    controls, and the run dialog's date picker and choices.
- Tests: `tests/test_workflow_paths.py` (27), `lib/quickEdit.test.ts`, `lib/inputKinds.test.ts`,
  and the e2e spec `workflow-quick-edit.spec.ts`.

## Not verified
- On a real Windows machine: the date picker and select controls in the desktop shell.

## Follow-ups
- Batches 2 to 5 of #776 (in `docs/plan.md`).
