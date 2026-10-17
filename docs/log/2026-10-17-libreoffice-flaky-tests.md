# LibreOffice conversion tests no longer flake (shipped)

Why: #399. Tests that convert a deck or document with LibreOffice failed once and passed on the CI
rerun, a different test each time, which made every PR's CI noisy.

## Shipped
- Cause: 11 tests ran `soffice` themselves, on its shared default profile. Two soffice processes on
  one profile hand the job to the first and the second converts nothing, so parallel pytest workers
  collided. The product code already gives each run its own profile (`evals.libreoffice.soffice_profile`).
- `tests/libreoffice_probe.py: convert_with_libreoffice` converts through that per-run profile; the 11
  tests in `tests/test_documents_tool.py` and `tests/tools/office/pptx/` use it.
- `tests/test_office_bins.py` fails if a test calls `soffice` directly again.
- Measured: the eight touched files with `-n 4` failed 4 of 26 tests on both runs before the change and
  passed 26 of 26 on three runs after.

## Not verified
- The Windows nightly (LibreOffice is not installed there; the tests skip).

## Follow-ups
- None.
