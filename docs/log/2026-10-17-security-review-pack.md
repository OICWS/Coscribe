# The security review pack (shipped)

Why: #348 item 7. The quarterly human security review (decision 0009) had no list of what to read.

## Shipped
- `docs/security/review-pack.md`: the invariant paths, the approval table (read from
  `tests/test_approval_decisions.py`), how secrets flow, the listeners, and the no-sandbox
  assumptions of 0002, each row with the code and the test that guards it, plus a short
  procedure for the reviewer.
- It records one open question found while writing it: the local server checks neither `Origin`
  nor `Host`. It was reported to the maintainer privately, not as a public issue.

## Not verified
- The statements about code were checked by reading it and by one probe against the test client;
  the attack the open question describes was not demonstrated end to end.

## Follow-ups
- Read the first scheduled `audit.yml` run (Monday 2026-10-19, 03:17 UTC) and the CodeQL alerts, and
  file one issue per real finding.
