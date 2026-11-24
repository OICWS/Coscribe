# The weekly numbers keep one issue current (shipped)

Why: `scripts/weekly_metrics.py` had run once (`docs/metrics/2026-W42.md`), so nobody saw whether
the tree stayed maintainable as it grew. Decision 0009 needs those numbers every week, and the
new limits (test selection, size budgets) need their own. Part of #1051, step 3.

## Shipped
- `.github/workflows/weekly-numbers.yml`: every Monday at 04:41 UTC the page for the week before
  becomes the body of the "Weekly numbers" issue. The run creates the issue once and then only
  edits it, so it adds no comment. A manual run takes a week (`2026-W47`); a pull request that
  changes the job or the script only prints the page.
- `scripts/weekly_metrics.py` adds three sections:
  - Test selection: each merged pull request's changed files run through `ci_scope.plan`, giving
    the scopes and the share of test files run. A full scope counts as the whole suite. The
    section also has the nightly selection audit's runs and failures.
  - The size budgets of `quality/budgets.json`: the core, the largest component, and every
    component at 80% of its budget or more.
  - The five component cards that the most commits to their code have passed since the card
    last changed.
  `--last` picks the week before this one.
- Size budgets now cover the frontend (`scripts/ratchet.py`, `quality/budgets.json`). Each
  feature folder (`frontend.<name>`) has the 20,000-line component budget; `workflow` is the
  largest at 9,553. The frame outside the features (31,722 lines today) has its own budget,
  `frontend_shell_lines`, set to 33,000, so a new screen goes into a feature folder. Tests are
  left out of the count.
- First run, by hand, for 2026-W47: 88 merged pull requests, 73 selected, 6 full, 9 docs only.
  They ran 38% of the 297 test files on average. The core is at 36% of its budget, and the
  `frontend` card is 10 commits behind.

## Not verified
- The scheduled run and its edit of the issue: the page was built here against the real API,
  and the issue step is the audit workflow's, which already runs weekly.
- The selection share uses the graph of the tree at the week's end, not each pull request's own
  tree, so a module added or removed during the week can shift a share a little.

## Follow-ups
- None.
