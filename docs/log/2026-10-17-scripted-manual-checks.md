# Eight of the 20 checks for a person have a scripted part; the rest are written as steps (shipped)

Why: issue #393 held 20 checks for a person on a real Windows machine (#402 item 8). Each was
tried once more for a script on the Windows runner.

## Shipped
- `.github/workflows/windows-more-checks.yml`, nightly and on a pull request that changes it,
  the tests or CODEOWNERS. Job `real-windows` runs `tests/test_windows_real.py` (skipped unless
  `COSCRIBE_WINDOWS_REAL=1`, so `windows.yml` is untouched) and fails if any test is skipped:
  the real Credential Manager (store, `cmdkey /list`, read back in a new process, entry removed),
  hooks under cmd and PowerShell, `Format-Hex` on Windows PowerShell 5.1 and the code module's
  read check, `taskkill /T` on a background command's process tree, a Store-stub-like `python`
  replaced by a working one, Chinese text drawn by resvg with YaHei. The no-Node message test
  also runs everywhere. Job `codeowners` fails when GitHub lists CODEOWNERS errors.
- Found on the way: `Format-Hex -Count` does not exist in Windows PowerShell 5.1; the code
  module's tests and the log of 2026-10-09 use it. The read check does not depend on it.
- `docs/manual-checks.md`: for each of the 20 checks what is scripted, and for the rest the
  steps, the expected result and the time.
- Shown to fail when broken (PR #408, closed): taskkill without `/T`, plaintext instead of a
  keychain reference, a Python lookup that ignores a broken stub, `Format-Hex` removed from the
  read list; and a CODEOWNERS line with an unknown owner.

## Not verified
- The hook and YaHei tests were not broken on purpose.
- The real Store alias and a conda-only Python: the test uses a `python.cmd` that exits 9009.
- Any check that needs Office, an account, a model key or the Electron window.

## Follow-ups
- Branch `tmp-break` (PR #408) is left for the maintainer to delete.
