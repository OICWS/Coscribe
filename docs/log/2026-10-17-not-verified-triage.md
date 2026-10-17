# The "Not verified" items are sorted and the human checks are one short list (shipped)

Why: #388 item 3. The log held 281 "Not verified" items; asking a person to read them all was not
a plan. Most were stale, already covered by a Windows run, or a stated limit.

## Shipped
- `docs/metrics/2026-10-17-not-verified-triage.md`: every one of the 281 items in one bucket. 111 go
  into 20 checks for a person, 52 are covered by the nightly Windows job, 6 died with decision 0012,
  5 moved into a script job, 2 are engineering follow-ups and 105 are limits the log already states.
- `.github/workflows/windows-checks.yml`: `lint-imports`, the two `--check` generators and
  `ratchet.py --enforce` (which includes knip and the TypeScript sizes) on a Windows runner, nightly
  and when the file changes. A separate workflow so a failure does not reset `windows.yml`'s green
  nights.
- `scripts/ratchet.py` starts knip through `knip.cmd` on Windows: the first Windows run failed with
  `WinError 193` on the POSIX script.
- The 10 area issues #376 to #385 are closed; one issue carries the 20 checks, each with steps.

## Not verified
- The new workflow's first run: the pull request that adds it is its first run, and the ratchet
  baseline may differ on Windows (line endings, path keys); a red first run says which.
- The sorting is my reading of each item, not a re-run; the per-item table in the triage file lets
  the maintainer overrule one.

## Follow-ups
- Make the new job green or fix what it finds, then add it to the required checks with `windows.yml`.
- Write a "Not verified" item only when a person must do something; the log README still allows
  a limit, which is how most of the 105 got there.
