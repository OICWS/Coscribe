# A key typed into a connector is blanked like a secret (shipped)

Why: the logs-and-databases part of manual check 11 (#844) was reproduced locally with a stdio
MCP server that echoes its keys. A key picked from Settings > Secrets came back blanked; a key typed
straight into the connector's env did not, and reached the tool result, the UI and the checkpoint
database. `SECURITY.md` promises connector tokens the same as secrets; `redactor` read only
Settings > Secrets.

## Shipped
- `SecretStore.blank_also(owner, values)` (`runtime/secret_store.py`): keys kept like a secret but stored elsewhere; every
  `redactor` blanks them and their encodings too (values under 8 characters are skipped, as for a
  secret). A header such as `Bearer <token>` also blanks the token alone.
- Wherever a connector's plaintext values are produced for connecting (`prepare_for_connect` when
  one connector is (re)connected, `load_mcp_server_configs` at startup), the credentials among them
  are handed to it: an env or header value whose name says so (`TOKEN`, `API_KEY`, `Authorization`,
  `X-Api-Key`, ...) or that looks like a token (20+ letters and digits, no path or URL). `MODE`,
  paths, base URLs and `Content-Type` stay readable, since the blanking reaches every tool result.
- `runtime_lg.mcp_oauth` hands it a hosted connector's access and refresh tokens. What an owner
  gave is kept for the life of the process, so a token replaced by a refresh stays blanked.
- Tests in `tests/test_connector_secrets.py`; the same echo server rerun locally: both keys now
  read `[REDACTED SECRET]` and neither is anywhere under the state folder.

## Not verified
- On Windows with a real hosted connector (Canva, Notion): the change is in shared code, not
  Windows-specific.

## Follow-ups
- A guided-setup app's `client_secret` (`set_app`) is not handed to `blank_also`; it goes only to
  the token endpoint, so a server has no way to echo it.
- A token under a name that does not say credential and containing `/` is not recognised by shape.
- A connector's values are blanked from the moment it connects in this process; text from before
  that, in an older conversation, is not rewritten.
