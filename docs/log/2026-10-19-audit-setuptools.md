# The audit no longer reports the runner's own setuptools (shipped)

Why: the first scheduled Audit (2026-10-19, run 4) opened issue #451 with one finding: `setuptools 79.0.1` (PYSEC-2026-3447, fixed in 83.0.0). Nothing in `pyproject.toml`, the lock or the shipped app asks for `setuptools`; it is the build tooling that `actions/setup-python` puts in the runner's Python. The app's own script-environment venv only hides `pip`, `setuptools` and `wheel` from the package list (`tools/exec/script_env.py`), it does not install them.

## Shipped
- `audit.yml` upgrades `setuptools` together with `pip-audit` and `pip-licenses`, so the report is about what we ship. No product code changed.

## Not verified
- This pull request's own Audit run is the check that #451 closes clean; the other audit jobs (npm, secrets, licences) were already green on 10-19.
