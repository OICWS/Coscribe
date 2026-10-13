# code_runtime: Codex as coscribe's second agent runtime, for code tasks

## Purpose
Owns getting Codex onto the machine (`install.py`: a pinned build fetched on first use, never
bundled; `_pins.py`: the versions and hashes), starting it (`launch.py`: its config and
environment, one shared `codex app-server` per state folder that stops when idle), talking to it
(`client.py`: JSON-RPC over stdio), one conversation's Codex thread (`thread.py`: a turn at a
time, every command and file change coming back as an approval), the app's handle on all of it
(`service.py`) and the Settings > Code policy (`permissions.py`). Does not own the approval cards
or the decision of what to allow (`conversation/approvals.py`, `runtime_lg/code_agent.py`) or the
settings routes (`web/routes/settings/code.py`).

## Public interface
`CodeService`, `code_service`, `remove_stale_code_sidecars`, `shutdown_code_services` (the app's
handle); `CodexUnavailable`, `codex_model` (installing and picking a model); `CodexThread`,
`CodexEvent`, `ApprovalRequest`, `shell_script` (driving a thread); `CodePermissions` (the
policy). Callers import these from `coscribe.code_runtime`, not a submodule. Tests still reach into
`client`, `launch` and `install` for fakes and private names (`CodexHost`, `LaunchSpec`,
`config_toml`, `codex_executable`); do not copy that into `src`.

## Depends on
`coscribe`, `coscribe.config`, `coscribe.runtime`, `coscribe.tools`.

## Invariants
- `permissions.py` is an invariant path (`office-agent/CLAUDE.md`): a change to it needs an
  independent review.
- The thread runs with no sandbox (`danger-full-access`, `docs/decisions/0002-approvals-not-a-sandbox.md`),
  so the caller's approval answer is the only gate; every action comes back to it
  (`tests/test_code_runtime.py::test_the_thread_runs_unsandboxed_with_every_action_coming_back`).
  The one exception is a plain read inside the thread's own folder, which runs without asking;
  a read outside it still asks (same file).
- A downloaded Codex member or wheel that does not match its pinned sha256 is not installed
  (`tests/test_code_runtime_install.py`).
- A fixed workflow run never reaches this package (import contract, `docs/decisions/0005-code-is-a-second-runtime.md`).
- Only `coscribe.web` knows about HTTP: this package never imports FastAPI, Starlette or uvicorn
  (import contract, `lint-imports`).

## Tests
`tests/test_code_runtime.py`, `tests/test_code_runtime_install.py`, `tests/test_code_agent.py`
(the runtime_lg side), `tests/test_approval_decisions.py` (the policy in the approval table),
`tests/web/test_settings.py` (the Settings > Code routes).

## Verify by hand
The whole module on a real Windows machine: first-use download of Codex, a task that runs a
PowerShell command and edits a file, an approval card for each, "allow" in Settings > Code, and
the shared app-server stopping when idle. No test starts a real Codex.

## Reviewed
2026-10-13 (first card).
