# 0059: A pull request runs the tests its change can reach; main runs them all

Status: proposed (2026-11-23, OICWS; the maintainer asked for the 0009 gaps to be closed in the
project thread). Narrows 0009's "full suite on every pull request" practice; 0006's required
`test` check is unchanged.

## Context
0009 aims at about 1M lines. Every pull request ran all 3,439 tests: 9 to 19 minutes on `main`
at 120k lines, so about an hour or more at 1M. The 2026-10-11 assessment (§3, CI speed, step 4)
planned test selection by changed component, with the full suite on `main` and nightly. GitHub's
merge queue, which would run the full suite before each merge, needs an organization (0009,
not decided).

## Decision
- `scripts/ci_scope.py` builds an import graph over `coscribe`, the tests, `evals` and
  `scripts`. An edge goes to the module that defines what is imported: a package `__init__.py`
  that only re-exports is an interface, not a dependency on all it lists; one that runs code is a
  dependency as a whole. Strings naming a module (`monkeypatch.setattr("coscribe.x.y", ...)`)
  are edges. A conftest's imports are edges of every test below it, followed only from a module
  that changed itself.
- A pull request runs the tests whose imports reach a changed module, the tests whose text names
  a changed file that is not Python, and the tests that read the whole tree (`ALWAYS`). A file
  inside `coscribe` that is not Python belongs to its package. A change the graph can't place
  (pytest configuration, the lockfile, a conftest, the workflows that run pytest, a file no test
  names) runs everything. The Linux `test` and the Windows `pytest` jobs select the same way.
- `main` and the nightly Windows run still run every test, and a selected-only pull request
  that turns `main` red is reverted by 0006's rule.
- `scripts/selection_audit.py` runs nightly: in three modules picked at random, every function
  raises; every test that then fails must be among those selected for that module. A miss fails
  the run and names the dependency the graph does not see.

## Consequences
- The coverage floor applies only when every test ran; changed-line coverage still reads the
  selected run.
- The relaxation for re-exporting packages is what makes selection useful: Python does run a
  parent's `__init__`, so a module that fails to import fails tests that were not selected.
  `mypy`, `ruff` and the module's own tests run on every pull request and catch that first.
- Selection shrinks as components stop importing through the composition root (`web.app`); the
  share of tests a change selects is a number to watch, not a guarantee.
