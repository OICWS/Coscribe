# An eval scores saved browser workflows against sites that change (#754; in review)

Why: a live test on one expense site, in five versions, found a fixed workflow failing loudly
and the investigation repairing it, and found two bugs (#752, #753). Fixing cases one site at a
time overfits to that site. Changes for P4 (failures climb, the autonomy setting) need a score
across sites and kinds of change.

## Shipped
- `evals/workflow/`: two form sites drawn from a description, with nine mutations that combine.
  Scenarios cross site, mutations and how the task is built: the recorded fixed steps, or a
  bounded agent step per row. The runner drives a running desktop app over its REST routes and
  a thread's WebSocket. When a run fails, it follows the run's investigation, approving and
  answering, and saves the last revision. It judges by what the site stored.
- `evals/README.md`: how to run it and what each verdict means.
- `tests/test_evals_workflow.py`: the sites, mutations, the recorded workflow and the judge.

## Not verified
- On Windows. Scored live on Linux with the desktop app under xvfb and `deepseek:deepseek-flash`.
