# A ratchet for numbers about the code, report only; the encoding rule is on (shipped)

Why: Step 1 of the structure period (record 0009). Numbers such as file size and cross-package imports sink a little with every change, and nothing noticed. The assessment (`docs/assessments/2026-10-11-scale-to-1m-lines.md`) asked for a baseline that numbers may only improve against.

## Shipped
- `office-agent/scripts/ratchet.py` measures seven things on our own code (vendored code left out) and compares them with `office-agent/quality/baseline.json`: files over 800 lines (11), functions over 100 lines (39) and over McCabe complexity 15 (27, from ruff's C901), suppression comments (`type: ignore` 43, `noqa` 142, `pragma: no cover` 2), imports that reach into another package's submodule or a private name (168), tests with no assert or `pytest.raises` (15), and `monkeypatch.setattr` on a dotted `coscribe.` string (23 files' worth). A number is worse when a name is new or its value grew. Runs in about 1.3 seconds.
- Report only: `scripts/check.sh` prints the comparison and never fails. `--enforce` makes a worse number fail and `--update` rewrites the baseline; the enforcing switch is for a week from now, once the numbers have been seen in CI.
- `quality/` and `scripts/ratchet.py` are in `CODEOWNERS`: raising a number loosens the rule and only a human approves that (0009).
- `ruff check --preview --select PLW1514` runs in `check.sh` (a text file opened without an encoding reads in the locale's code page on Windows). It is run on its own because `preview = true` in the config also changed other rules (it flagged `__all__` names that are provided lazily). The one violation, in `tests/test_code_runtime.py`, is fixed.
- Nine tests in `tests/test_ratchet.py`: what counts as worse or better, and each metric on a small tree. The test of the metric that counts string patches builds its sample text so the ratchet does not count the test itself.

## Not verified
- That the numbers match the assessment's: they agree where it gave one (15 tests with no check; the file sizes; 165 deep imports against 168 here, which also counts private-name imports).
- The effect in CI: it prints one line there.

## Follow-ups
- After a week of numbers: `--enforce` in `check.sh`; then the other ratchets in the assessment (size and complexity budgets as a per-file baseline, import contracts per package).
