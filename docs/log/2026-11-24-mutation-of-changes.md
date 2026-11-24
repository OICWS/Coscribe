# Mutation testing of what a pull request changed (shipped)

Why: the nightly mutation run covers seven fixed modules, so a pull request's new code in any
other module was only checked by coverage, which shows that a line ran, not that a test would
notice it changing. Follow-up to #1051 (the 2026-11-23 assessment's point 5).

## Shipped
- `scripts/mutation.py changed --base SHA --out DIR`: for each module under `src/coscribe` whose
  functions the diff changed (at most 5), it runs mutmut on the mutants of those functions only
  (mutmut 3 names them `x_<function>__mutmut_<n>` and `xǁ<Class>ǁ<method>__mutmut_<n>`). It uses
  the tests that import the module, or else every test `ci_scope` says reaches it. The scratch
  copy now also holds `evals/` and `scripts/`, which some tests import.
- `.github/workflows/mutation-changes.yml` runs it on a pull request that changes Python under
  `src/coscribe` and puts the table in the run summary. The survivors' diffs are in the
  `mutation-changes` artifact. It reports and never fails: some mutants change nothing a test
  could see. `office-agent/CLAUDE.md` says what to do with each survivor.
- Replayed on 5fdeb14 (the NO_PROXY change to `runtime/proxy.py`): 61 mutants in the changed
  functions, 27 killed, 10 survived, 24 that no test reaches (the Windows registry branch), in
  32 seconds.

## Not verified
- The workflow itself until it runs on a pull request that changes `src/coscribe`; this one
  changes only the script, so its run mutates nothing.

## Follow-ups
- None.
