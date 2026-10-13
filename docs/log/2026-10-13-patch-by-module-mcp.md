# The MCP and tool-deferral tests patch module objects, not string paths (partly shipped)

Why: part 2 of issue #100. A string-path `monkeypatch.setattr("coscribe.x.y.name", ...)` keeps passing when `name` moves, and the planned splits of the large modules will move many of them.

## Shipped
- The 10 string-path patches in `tests/test_mcp_lg.py` (8), `tests/test_connector_secrets.py` (1) and `tests/test_tool_deferral.py` (1) now patch `runtime_lg.mcp` (and its `shutil`) or `conversation.session` as module objects. No change under `src/`; no test checks anything different.
- Those three files are gone from `patch_by_string` in `quality/baseline.json`.

## Not verified
- Windows: ran on Linux only.

## Follow-ups
- The remaining groups of issue #100.
