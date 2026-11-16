# Tests no longer write to the Windows runner's real keychain (shipped)

Why: on the Windows `pytest` job, tests that store a key without a fake keychain wrote to the
runner's real Credential Manager, and some failed when the entry was missing on read
(`tests/web/test_webhook.py` on #918, `test_connectors` on #883). Linux CI has no keychain service, so
the same tests there never touch one.

## Shipped
- `tests/conftest.py`: an autouse fixture sets keyring's do-nothing backend on Windows for every test,
  as Linux already has. Tests that fake the keychain still install their fake on top; the real-Windows
  checks (`COSCRIBE_WINDOWS_REAL=1`, `tests/test_windows_real.py`) keep the real Credential Manager.

## Not verified
- Why the runner's Credential Manager lost entries; this keeps tests from depending on it rather than
  explaining it. Windows CI is the check.
