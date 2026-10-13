# Nightly mutation testing on seven invariant modules (shipped)

Why: Coverage shows code ran, not that a test checked it. Issue #115 asks for a nightly report of the changes (a `<` to `<=`, a deleted line) that no test notices, for the modules where a silent mistake is a security or data problem.

## Shipped
- `.github/workflows/mutation.yml`: nightly, `workflow_dispatch` and a pull request that changes the job itself, Linux, not a required check, one matrix job per module (25 minute limit each; the matrix is read from `MODULES` by a setup job) plus a summary job that writes the table to the job summary and uploads the survivor lists as the `mutation-survivors` artifact.
- `office-agent/scripts/mutation.py`: runs mutmut 3.8.0 on one module inside a scratch copy of `src/` and `tests/` whose `pyproject.toml` gets a `[tool.mutmut]` section naming that module and its own tests (mutmut reads one config from the current directory, so one module per run needs one copy). The package is deliberately not installed in the job: an editable install would shadow the mutated copy.
- Modules and the tests that own them are the `MODULES` table in the script. Running the whole suite is wrong: mutmut's trampolines break `tests/test_tool_deferral.py`, which reads tool schemas from function signatures.
- Local run, 4 cores: 1859 mutants, 1283 killed, 550 survived, 4 timed out, 22 not reached by any test; the slowest module (`_xlsx_lookup_formulas.py`) took about 3 minutes.
- A run whose tests fail before any mutation, or that stops early, writes no result for its module; the summary names it as missing instead of showing a green row.

## Not verified
- Windows: mutmut forks, so this is Linux only by design; the product is not affected.

## Follow-ups
- One issue per module with survivors, opened after merge from the first nightly run. The killing tests are not part of this change.
