# load_skill points a plugin's services to Coscribe's connectors (shipped)

Why: step 6 of #1036 (decision 0058). A Claude or Codex plugin names the MCP servers its skills
use; Coscribe never starts them, so the model needs to know which service a skill expects and
how to reach it here.

## Shipped
- `tools/skills.py`: loading a plugin's skill adds one fixed sentence when the plugin declares
  servers (its `.mcp.json`, or `mcpServers` in its manifest): their names and hosts, that
  Coscribe does not start them, and to call `find_connector` and `offer_connector` if no tool
  reaches the service. Only a single short word per name and host passes, at most eight, so the
  file cannot add sentences of its own. No tool schema changed.
- Checked with DeepSeek in the app: a test plugin for Notion meeting notes; the model loaded the
  skill, found the Notion connector and showed its Connect card, with the summary written.

## Not verified
- On Windows.

## Follow-ups
- Step 7 of #1036: export a plugin as a `.zip`.
