# A key typed into a connector is blanked like a secret (shipped)

Why: the logs-and-databases part of manual check 11 (#844) was reproduced locally with a stdio
MCP server that echoes its keys. A key picked from Settings > Secrets came back blanked; a key typed
straight into the connector's env did not, and reached the tool result, the UI and the checkpoint
database. `SECURITY.md` promises connector tokens the same as secrets; `redactor` read only
Settings > Secrets.

## Shipped
- `runtime.blank_also(owner, values)`: keys kept like a secret but stored elsewhere; every
  `redactor` blanks them and their encodings too (values under 8 characters are skipped, as for a
  secret). A header such as `Bearer <token>` also blanks the token alone.
- `tools.mcp.prepare_for_connect` hands it every env and header value a connector is started with;
  `runtime_lg.mcp_oauth` hands it a hosted connector's access and refresh tokens.
- Tests in `tests/test_connector_secrets.py`; the same echo server rerun locally: both keys now
  read `[REDACTED SECRET]` and neither is anywhere under the state folder.

## Not verified
- On Windows with a real hosted connector (Canva, Notion): the change is in shared code, not
  Windows-specific.

## Follow-ups
- A connector's values are blanked from the moment it connects in this process; text from before
  that, in an older conversation, is not rewritten.
