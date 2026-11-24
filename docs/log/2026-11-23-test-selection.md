# A pull request runs the tests its change can reach (shipped)

Why: every pull request ran all 3,439 tests (9 to 19 minutes on `main` at about 120k lines),
which grows with the code toward the 1M lines of decision 0009. Decision 0059; part of #1051,
step 1.

## Shipped
- `scripts/ci_scope.py` builds an import graph over `coscribe`, the tests, `evals` and
  `scripts` and prints `scope=docs|selected|full`, with `--tests` the files to run. An edge goes
  to the module defining what is imported; a package `__init__` that only re-exports is not a
  dependency on all it lists. Strings naming a module and a conftest's imports count. A file that
  is not Python is matched by name (inside `coscribe`, by its package); one nothing places runs
  every test.
- `office-agent-ci.yml` and `windows.yml` pass the selection to pytest (`COSCRIBE_TESTS` in
  `check.sh`); the coverage floor is measured only when every test ran. `main` and the nightly
  Windows run still run all.
- `scripts/selection_audit.py` and `test-selection-audit.yml` (nightly): in three random modules
  every function raises, the whole suite runs, and each failing test must be one the selection
  picks. Run here on four modules (`runtime/dotenv_file.py`, `conversation/turn_record.py`,
  `web/routes/files.py`, `workflow_spec/reads.py`): 56, 58, 55 and 36 test files failed, all of
  them selected (66, 97, 66 and 138 selected).
- Measured over the last 150 commits on `main` against one full run's timings: 120 would run a
  selection, 16 everything (lockfile, `pyproject.toml`, conftest, the pytest workflows), 14 only
  the docs tests. On average a pull request runs 40% of the test files and 58% of the test time;
  the median is 75% of the time, because most code reaches the composition root (`web.app`,
  `coordinator`) through which the web and conversation tests import nearly everything.

## Not verified
- The Windows job's selection on a Windows runner: it runs the same script under `bash`, which
  the job already uses.

## Follow-ups
- The selection share is a measure of coupling: tests that reach the code through `web.app`
  rather than the component's interface keep it high. The weekly numbers (#1051, step 3) track it.
