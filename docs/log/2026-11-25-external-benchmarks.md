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
- Batch 1, the rest of OfficeVal: 93 tasks graded in all. 6 need Word through COM, and 061's
  input video is missing upstream. Mean 0.48: Word 0.61, Excel 0.49, PowerPoint 0.39. About $8 in
  all, $0.08 a task. The 48 tasks with a picture scored 0.41, which led to `look_at_image` (#1088).
- `evals/AGENTS.md`: how to keep an eval's cost down. Ask before a large run, rerun only the dev
  tasks a change can reach, check for free where possible, and cut model calls per task.
- `tests/test_evals_external.py` for the parts that need no model or download.

## Not verified
- The six OfficeVal tasks whose verifiers need Word through COM; they are skipped off Windows.
- SpreadsheetBench beyond batch 0 and our own tasks: they run in batches once each is approved.

## Follow-ups
- Run the remaining OfficeVal tasks, 100 stratified SpreadsheetBench tasks and our own tasks,
  then fix the lowest-scoring areas (`docs/plan.md`).
- SpreadsheetBench 359-21: the agent wrote a faster macro into the answer sheet instead of
  doing the deletion it describes.
