# E2E runs on a pull request that changes a spec (shipped)

Why: the first scheduled run of `slides.spec.ts` (night of 10-18) failed in the text-box step, although the same spec had passed in its pull request. A flaky step surfaced only at night, and a night is a day lost.

## Shipped
- `e2e.yml` also runs on a pull request that changes `frontend/tests/e2e/` or `scripts/stub_llm.py`, not only this file.
- `slides.spec.ts` waits for the new text box to hold focus before typing (typing earlier goes nowhere, and the page then never gains the text).

## Not verified
- The runner: the failure did not reproduce locally (8 passes in a row), so the focus wait is the likely cause, not a proven one. This pull request's own E2E run, and the next night, are the check.
