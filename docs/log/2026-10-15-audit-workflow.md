# A weekly audit of dependencies, licences and secrets (shipped)

Why: #232 item 7, guardrail 9 of the assessment (dependency, licence and secret scanning).

## Shipped
- `.github/dependabot.yml`: weekly version-update pull requests for `office-agent` (pip), the frontend and the desktop shell (npm) and the workflows, patch and minor grouped.
- `.github/workflows/audit.yml`, weekly (Monday 03:17 UTC), by hand, and on a pull request that changes it. Four jobs and a report:
  - `pip-audit` on the installed Python dependencies;
  - `scripts/check_licenses.py` on `pip-licenses`: fails on GPL, AGPL and SSPL, allows LGPL and MPL, lets a dual licence pass when it offers a permissive option, lists packages with no licence metadata;
  - `npm audit --omit=dev --audit-level=high` for the frontend and the desktop shell;
  - gitleaks 8.30.1 (pinned, sha256 checked) on the tree with `.gitleaks.toml`: the default rules, and an allowlist of the files whose matches are test fixtures, the vendored animation catalog's ids and Bitbucket's public client id.
- The report job writes the run summary and keeps one issue, "Audit findings": opened or updated by the weekly and manual runs, closed when a run is clean. A pull request run only prints.
- Proved by breaking: a planted GitHub-token-shaped string in a source file makes gitleaks exit 1 on a clean checkout, the clean checkout exits 0; a GPL package in the licence input makes the licence check exit 1 (and `tests/test_check_licenses.py` covers the classification). Local `pip-audit` on a development environment found `langchain-openai` 1.1.9 and `langsmith` 0.8.5; the lower bounds in `pyproject.toml` let CI install the fixed versions, so the first CI run decides whether an issue is opened.

## Not verified
- The workflow itself: it can only run once it is on GitHub (the pull request run prints the result; the issue step runs on the first scheduled or manual run). npm licences are not checked.

## Maintainer's settings
- Turn on Dependabot security updates, secret scanning and push protection under Settings, Code security. These are repository settings and not in code.
- The workflow files are CODEOWNERS paths.
