# The ratchet can no longer loosen itself (shipped)

Why: a second review of the structure period found that `ratchet.py --update` wrote every
measured number, worse ones included, and its own message told a session to run it whenever
something improved. A pull request that improved one number and worsened another therefore
moved the baseline in the wrong direction, behind a diff of about 300 entries.

## Shipped
- `scripts/ratchet.py --update` refuses to write when any number got worse;
  `--update --accept-worse` is the maintainer's flag. Four tests in `tests/test_ratchet.py`.
- `scripts/check.sh` runs `ratchet.py --enforce`, so CI fails a pull request with a worse
  number. Nothing is worse on `main` today.
- `pyproject.toml` (import contracts, coverage floor) is a CODEOWNERS path, as 0009 says.
- The Windows run is red when a test fails (job-level `continue-on-error` removed); it is
  still not a required check.
- `AGENTS.md` says two known upward imports, not three; `plan.md` calls 0008 accepted.

## Not verified
- How often `--enforce` will fail a legitimate rename (a renamed long function counts as new);
  the maintainer decides each case with `--accept-worse`.

## Follow-ups
- Changed-line coverage (diff-cover) stays report-only: count how many recent pull requests
  would have failed 80% first.
- The snapshot of tool schemas stores hashes only; a readable form is the next hardening.
