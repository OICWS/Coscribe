# The announce-a-failed-run test gets a full wait of its own (shipped)

Why: the Windows night of 10-24 failed one test, `test_a_failed_run_of_a_task_set_to_is_looked_into_and_announced_lg`, which restarts the 14-night clock of #232.

## Shipped
- `tests/web/test_scheduled.py`: the test read the saved reply for at most 10 s counted from the start of the test, which also covered the run itself. It now waits up to 30 s for the model's third call and up to 30 s, counted again, for the reply to be saved. The limit only stops a hang; no assertion is about elapsed time.
- `docs/plan.md`: the Windows line records the 10-24 night.

## Not verified
- The cause is likely, not proven: the failure log shows the earlier assertions passing and only the saved reply missing, and the test took 9.6 s on a cold local run. It did not fail locally (the test passes in 2.6 s warm), so there is no proof by breaking. The next scheduled Windows run is the check.

## Follow-ups
- If it fails again with the full wait, the reply is not being saved on Windows and that is a product bug to trace.
