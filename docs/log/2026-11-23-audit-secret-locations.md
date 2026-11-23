# The weekly audit names the file and line of each suspected secret (shipped)

Why: the audit run of 2026-11-23 opened "Audit findings" (#1045) with gitleaks' summary only
("leaks found: 4"), so nobody could tell from the issue where the matches were or whether they
were real.

## Shipped
- `.github/workflows/audit.yml`: gitleaks writes a JSON report (still `--redact`), and the
  secrets section of the issue lists one line per finding, `file:line  rule`, with no part of
  the value. If gitleaks fails before scanning, its log goes into the issue instead.
- `.gitleaks.toml`: the four findings were test or CI placeholders, now allowlisted:
  `office-agent/tests/test_connector_secrets.py` (two made-up keys the redaction tests feed in)
  and the fixed `e2e-launch-token` that `e2e.yml` and `windows-more-checks.yml` give a
  throwaway local server (allowlisted by value, so a real token in a workflow still reports).

## Not verified
- The issue step itself (it only runs on the schedule or by hand, not on a pull request); the
  scan and the report lines were run locally with gitleaks 8.30.1 against `main`.
