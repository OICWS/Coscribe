# Public office benchmarks run through coscribe's agent (shipped)

Why: our own eval tasks are written by us (#1072). Two public sets, with tasks and checkers
written by someone else, give a score others can compare.

## Shipped
- `office-agent/evals/external.py`: runs OmegaUse-OfficeVal and SpreadsheetBench Verified tasks
  through the real agent session that `evals.run` uses, and grades each with the benchmark's own
  checker (OfficeVal's verifier on the changed Office files; SpreadsheetBench's
  `compare_workbooks` after a LibreOffice recalculation). Neither dataset is copied here.
- Batch 0 on `deepseek-flash`, off-peak: OfficeVal 5 tasks, mean completion 0.84, $0.28;
  SpreadsheetBench 5 tasks, 3 of 5 right, $0.10. About 2 to 6 cents a task.
- `tests/test_evals_external.py` for the parts that need no model or download.

## Not verified
- The six OfficeVal tasks whose verifiers need Word through COM; they are skipped off Windows.
- The full sets: only batch 0 has run; the rest runs in batches once each is approved.

## Follow-ups
- Run the remaining OfficeVal tasks, 100 stratified SpreadsheetBench tasks and our own tasks,
  then fix the lowest-scoring areas (`docs/plan.md`).
- SpreadsheetBench 359-21: the agent wrote a faster macro into the answer sheet instead of
  doing the deletion it describes.
