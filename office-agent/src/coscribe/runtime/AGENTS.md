# runtime: the pieces every layer shares (secrets, hooks, tool metadata, provider config)

## Purpose
Owns where secret values live (`secrets.py`: the OS keychain behind `keyring` with a plain-file
fallback for provider keys; `secret_store.py`: the global Settings > Secrets, the per-session
choice of which may be used, and the `redactor` that blanks a value in output), lifecycle hooks
(`hooks.py`), the risk metadata every tool carries and the agent definition (`types.py`), custom
provider files (`provider_config.py`), the proxy setting (`proxy.py`), the `/compact` prompt
(`compaction.py`) and a context-window lookup (`llm_client.py`). Does not own any agent loop,
approval, tool or route: those are `runtime_lg`, `tools` and `web`.

## Public interface
Secrets: `store_secret`, `resolve_secret`, `delete_secret`, `harden_file_permissions`,
`env_value_for_storage`, `env_resolve_secret_for_display`, `env_delete_secret_if_ref`,
`resolve_env_keyring_refs`; the secret store: `SecretStore`, `SessionEnvironments`, `SecretError`,
`KeychainUnavailable`, `keychain_available`, `MIN_VALUE`, `host_allowed`, `placeholders_in`,
`substitute`, `redactor`. Hooks: `HookResult`, `empty_hooks_config`, `load_hooks_config`,
`run_hook`. Types: `Agent`, `ToolMetadata`, `tool_metadata`, `get_tool_metadata`. Other:
`LLMClient`, `load_custom_providers`, `configured_proxy`, `COMPACT_INSTRUCTIONS`.
Callers import these from `coscribe.runtime`, not from a submodule; tests may still reach into
a submodule for a private name or to patch it.

## Depends on
No other coscribe package.

## Invariants
- Only `runtime.secrets` imports the keychain (import contract "Only runtime.secrets talks to
  the OS keychain", checked by `lint-imports`).
- `runtime` never imports LangChain, LangGraph, FastAPI, Starlette or uvicorn (import contracts).
- A secret's value is stored in the keychain and nowhere else; a machine with no keychain
  refuses to save one (`tests/test_secret_store.py`). Provider and connector keys may fall back
  to a plaintext file with owner-only permissions (`tests/test_secrets.py`). The promise is only
  that the model cannot see a value, not that code that digs cannot find it.
- `redactor` blanks a stored value (and its common encodings) out of text, best effort
  (`tests/test_secret_redaction_properties.py`).

## Tests
`tests/test_secrets.py`, `tests/test_secret_store.py`, `tests/test_secret_redaction_properties.py`,
`tests/test_connector_secrets.py`, `tests/test_hooks.py`, `tests/test_provider_config.py`,
`tests/test_proxy.py`, `tests/test_llm_client.py`; the secrets routes through the server are in
`tests/web/test_settings.py`.

## Verify by hand
The Windows Credential Manager: save a secret in Settings > Secrets, find the entry there, restart
the app and use it; a hook command that runs under the Windows shell.

## Reviewed
2026-10-13 (first card).
