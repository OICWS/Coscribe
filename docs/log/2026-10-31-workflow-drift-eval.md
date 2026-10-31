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
- `--mark-submit` marks the final submit irreversible (decision 0029) and `--autonomy` sets the
  fixed workflows' autonomy (decision 0030, self-healing in #760), scored as `HEALED` when a healed run filed
  every row right; both need those changes in the app.
- `tests/test_evals_workflow.py`: the sites, mutations, the recorded workflow and the judge.

## Baseline (28 scenarios, `deepseek:deepseek-flash`)
- Fixed steps: PASS 4, REPAIRED 8, SAFE_STOP 2; no false success. Every repair's test runs filed
  2 or 3 real records on the site, and 3 of the 8 revisions had lost their task (#752).
- Agent step per row: PASS 11, SAFE_STOP 2, FALSE_SUCCESS 1. In that one the agent refused to
  tick "I have the receipt", stopped and said so, but reported `{"reference": ""}`. An empty
  text field passes the step's check, so the run said completed with a row unfiled.
- Where a required value was missing, the investigation added a check that stops the run
  before anything is sent and names the rows and the value; it invented none.

## After P4 (#756 agent outcome, #758 irreversible steps; `--mark-submit`)
- Fixed steps: PASS 4, REPAIRED 8, SAFE_STOP 2, as before, but the repairs' test runs filed 0
  records (were 2 or 3 each): they stop before the marked submit. 3 of 8 revisions still lost
  their task; #752 fixes that and wasn't in this build.
- Agent step per row: PASS 12, SAFE_STOP 2, FALSE_SUCCESS 0.
- Where a value was missing, nothing was invented: revisions report the rows as blocked and name
  the column the sheet needs.

## Not verified
- On Windows. Scored live on Linux with the desktop app under xvfb and `deepseek:deepseek-flash`.
