# Coverage is measured in CI; two tests no longer wait a minute each (shipped)

Why: Step 2 of the structure period (record 0009). Nothing measured how much of our own code the tests reach, and `tests/test_mcp_lg.py` spent almost all of its 122 seconds waiting for two real 60-second timeouts.

## Shipped
- `pytest-cov` in the dev extras; `[tool.coverage]` in `pyproject.toml` counts statements and branches of `coscribe`, leaving out the vendored code (`tools/_native_*/`, `providers/gemini_provider.py`).
- Measured on 2026-10-11, full suite: 1858 passed in 13 minutes with coverage, **89%** (statements and branches together, our own code). `fail_under = 85` for now, below the measured number because CI may lack tools a local run has; raise it to the number CI reports.
- `scripts/check.sh` runs pytest with coverage when `COSCRIBE_COVERAGE` is set (CI sets it; local runs stay as fast as before). On pull requests CI prints, report only, which of the lines the pull request changed the tests do not reach (`diff-cover`, all history fetched for it).
- The two timeout tests passed the short timeout through a module constant, but the function had bound its default when it was defined, so each still waited 60 seconds. They pass `connect_timeout` as an argument now: the file runs in 1.2 seconds instead of 122.

## Not verified
- The workflow steps (`diff-cover` on a pull request) have not run in GitHub Actions yet; the first run of this pull request is the test. `diff-cover` itself was run locally against the generated `coverage.xml`.
- Whether CI's number matches the local 89%.

## Follow-ups
- Raise `fail_under` to CI's number; make the changed-lines check fail under 80% after a week of numbers (assessment, step 2).
- Run pytest in parallel (step 6): needs the tests proven independent first.
