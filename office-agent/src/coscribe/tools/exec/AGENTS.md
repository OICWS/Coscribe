# tools.exec: Python and Node script tools, their environments and the folder guard

## Purpose
Owns `run_python_script` and `run_node_script` (`scripts.py`, `node_scripts.py`), the dedicated
Python venv and the npm directory the scripts run in (`script_env.py`, `node_env.py`) and the
guard that catches a script's mistaken writes outside the conversation's folders
(`script_guard.py`). Does not own the background-command tool (`tools/background_tasks.py`,
which uses the same environments), the approval policy for scripts (`runtime_lg/exec_policy.py`)
or the Settings routes that install packages (`web/routes/settings/environments.py`).

## Public interface
`build_script_tools`, `build_node_script_tools`, `ensure_script_env`, `ensure_node_env`,
`venv_python`, `overlay_env`, `resolve_python_command`, `suggested_folder`. Import them from
`coscribe.tools.exec`. The package-install functions (`install_package`, `list_packages`,
`uninstall_package`) and the guard helpers are still imported from their submodules.

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
