# tools.exec: Python and Node script tools, their environments and the folder guard

## Purpose
Owns `run_python_script` and `run_node_script` (`scripts.py`, `node_scripts.py`), the process they wait on, which the person can hand to the background tasks (`running.py`), the dedicated
Python venv and the npm directory the scripts run in (`script_env.py`, `node_env.py`) and the
guard that catches a script's mistaken writes outside the conversation's folders
(`script_guard.py`). Does not own the background-command tool (`tools/bookkeeping/background_tasks.py`,
which uses the same environments), the approval policy for scripts (`runtime_lg/exec_policy.py`)
or the Settings routes that install packages (`web/routes/settings/environments.py`).

## Public interface
`build_script_tools`, `build_node_script_tools`, `ensure_script_env`, `ensure_node_env`,
`venv_python`, `overlay_env`, `resolve_python_command`, the package-install functions
(`install_python_package`, `list_python_packages`, `uninstall_python_package` and the `_node_`
twins), the interpreter overrides (`get_interpreter_override`, `set_interpreter_override`,
`working_interpreters`, `fallbacks_for_platform`), the folder-guard helpers (`suggested_folder`,
`blocked_write`, `refusal_note`, `node_guard_args`, `writable_roots`, `write_python_wrapper`,
`without_guard_warnings`) and `run_python_script`, and for letting a running script go on in the background (`running.py`) `RunningCommand`, `Detachable`, `HandOff`, `request_detach`. Import them from `coscribe.tools.exec`.

## Depends on
`coscribe.runtime`, `coscribe.tools._files_written`, `coscribe.tools._output_truncation`.

## Invariants
- No sandbox: scripts run as the user, with the user's files and network. The folder guard is a
  mistake catcher, not a security boundary (`docs/decisions/0002-approvals-not-a-sandbox.md`).
- Both script tools carry the `EXEC` risk tier; approvals read it.
- Tool schemas are fixed and snapshotted (`tests/tool_schemas.txt`).

## Tests
`tests/test_scripts_tool.py`, `tests/test_node_scripts_tool.py`, `tests/test_script_guard.py`,
`tests/test_script_env.py`, `tests/test_node_env.py`, `tests/test_env_lock.py`.

## Verify by hand
A script run on Windows with no Python or Node installed; a package install from Settings.

## Reviewed
2026-10-17 (first card).
