# The desktop app carries its own command sandbox, so commands need no Codex download (shipped)

Why: the command sandbox was part of Codex, so a person who wanted sandboxed commands but not the
code module still downloaded Codex (302 MB). Codex's sandbox is a separate Apache-2.0 crate
(issue #607).

## Shipped
- `office-agent-sandbox/`: `coscribe-sandbox.exe` (`run`, `setup`, `uninstall`), built from
  `codex-windows-sandbox` at the tag in `CODEX_TAG` inside Codex's workspace, so Codex's
  Cargo.lock pins its dependencies. `scripts/build.sh OUT_DIR` puts it, the two helpers the crate
  launches and Codex's licence in one folder.
- `tools/exec/command_sandbox.py`: with `COSCRIBE_SANDBOX_DIR` set, commands run through it with
  the profile as a JSON policy file, and setup and uninstall use it; without it, Codex is
  downloaded as before. `GET /api/command-sandbox` says which (`source`), and Settings drops the
  download step and the "part of Codex" note when it is built in.
- The desktop build builds it into `resources/sandbox` and the app points the server at it.
- Windows more checks: a `builtin-sandbox` job builds it and runs `test_windows_real.py` against
  it. Decision 0022 updated.

## Not verified
- The installer itself: the desktop build is manual-only, so the packaged app was not built here.
- The Rust code was compiled only on the Windows runner (its dependencies don't build for Windows
  from Linux).
