# A pass on a real Windows machine over recently merged work (shipped)

Why: most merged pull requests say Windows was not verified. Instead of editing those
descriptions, this records once what was checked on the maintainer's own Windows computer.

## Shipped
- Environment, 2026-11-22: Windows 11 Pro (10.0.26300), Microsoft Office Home and Student 2021,
  Python 3.11.9, Node 24, Edge as Playwright's browser, the stub model (no real model calls).
- Office through COM (#855, #664, #1028): .docx, .xlsx and .pptx each converted to PDF by Word,
  Excel and PowerPoint; a conversion that timed out left a Word the person had open running.
- `tests/test_windows_real.py` with `COSCRIBE_WINDOWS_REAL=1`: 15 passed (Credential Manager, cmd
  and PowerShell hooks, taskkill of a process tree, the Store Python stub, a conda Python, YaHei,
  LibreOffice download, Edge page check).
- The system proxy (#672): read from Windows' Internet Options; a `NO_PROXY` on its own hid it,
  fixed in #1033.
- Side chat (#1024), `/fork` (#1029) and the effort picker (#1030): their Playwright specs pass
  against a local server, and screenshots were looked at.
- Scripts in the AppContainer: every run failed on Python 3.13+ (`mkdtemp`'s owner-only ACL),
  fixed in #1031.
- The desktop app: `npm run dist:portable` with the command sandbox built from source; the
  portable app starts and its server answers.

## Not verified
- The native folder picker, tray notifications and the command sandbox's setup that asks an
  administrator (the six `test_windows_real.py` checks that need one were not run).
- The four `test_windows_real.py` checks that download Codex: the local proxy dropped the
  download.
- Simple mode (#1027), not merged at the time.

## Follow-ups
- `slash-menu.spec.ts` "/clear archives the conversation": failed twice on this machine (the page
  stayed on the old conversation after Enter); in `docs/plan.md`.
- Tests that call `prepare_env` read the computer's real `%APPDATA%\Coscribe\.env` when the
  working folder has none; in `docs/plan.md`.
