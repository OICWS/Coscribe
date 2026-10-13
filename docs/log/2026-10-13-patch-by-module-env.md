# The script, node, convert and web-search tests patch module objects, not string paths (partly shipped)

Why: part 3 of issue #100. A string-path `monkeypatch.setattr("coscribe.x.y.name", ...)` keeps passing when `name` moves, and the planned splits of the large modules will move many of them.

## Shipped
- The 9 string-path patches in `tests/test_script_env.py` (4), `tests/test_node_env.py` (1), `tests/test_convert_tool.py` (1) and `tests/test_websearch_tool.py` (3) now patch the module (or the stdlib module it holds) as an object. No change under `src/`; no test checks anything different.
- Those four files are gone from `patch_by_string` in `quality/baseline.json`.

## Not verified
- Windows: ran on Linux only. The two `sys.platform` patches stand in for it.

## Follow-ups
- The remaining group of issue #100.
- Three patches did not matter to their test (see the pull request): `sys.executable` in two `test_script_env.py` tests, `sys.platform` "linux" in one.
