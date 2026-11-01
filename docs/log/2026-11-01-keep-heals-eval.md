# The workflow eval scores whether a kept heal holds on the next run (#754)

Why: #762 and #763 keep a run's heals in the task, as saved fixes or a drafted revision, so the
next run shouldn't need the same heal. Only a run after the keeping shows whether it does.

## Shipped
- `evals/workflow/run.py`: `--keep-heals` (with `--autonomy`). After a healed run that filed
  every row right, it saves the fixes the run's report offers, asks for a revision of the heals
  they can't keep (approving and answering as for a repair), and runs the task again.
  `rerun_verdict` scores that run: `PASS` with no heal, `HEALED_AGAIN`, `FAILED` or
  `FALSE_SUCCESS`.
- `evals/README.md`: the flag and its column.
- `tests/test_evals_workflow.py`: both kinds of keeping, then the next run; nothing is run again
  when the report offers nothing to keep.

## Result (14 fixed scenarios, `--autonomy self_healing --mark-submit`, `deepseek:deepseek-flash`)
- First runs: PASS 4, HEALED 2, SAFE_STOP 2, FAILED 6, the same counts as the last healing run.
- Both healed runs, once their heals were kept, ran again and filed every row with no heal:
  - suppliers, relabelled: the 8 healed steps were saved as fixes from the report.
  - expenses, a review page and a new reference format: the arguments were saved as fixes, and
    the review page was drafted as a revision in a conversation. Its test stopped before the
    marked "Confirm and send" and filed nothing; the revision stayed tied to its task.
- expenses, relabelled, healed in the last run and failed in this one: its first heal worked,
  then the run stopped at the next relabelled field. That is the first run's variance, not the
  keeping.

## Not verified
- On Windows. Scored live on Linux with the desktop app under xvfb.
- Two healed scenarios is a small sample; the six first-run failures are still healing's to fix.
