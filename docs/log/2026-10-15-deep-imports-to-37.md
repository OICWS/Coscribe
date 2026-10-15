# deep_imports 82 to 37

Importers now take a name from the package it lives in (`from ..tools import X`) wherever the
package already exported it, and `tools` exports the few names that several importers reached
into submodules for: `WorkspaceScope`, `enabled_skill_names`, `ensure_script_env`, `venv_python`
and the scheduled-trigger writes. `connect_mcp_tools_lg` stays a deep import on purpose: the
package exports it lazily to keep startup fast, which type checking cannot see through.
`tools/__init__` is at 25 imported modules, the ratchet's fan-out limit, so the next export there
needs a smaller package or a lazy name.
