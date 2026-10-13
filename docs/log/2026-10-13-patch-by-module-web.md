# The web tests patch module objects, not string paths (partly shipped)

Why: `monkeypatch.setattr("coscribe.x.y.name", fake)` keeps passing when `name`
moves or is imported under another name, and the splits of `session.py` and
`app.py` will move many of them. Issue #100 replaces all of them, one area per PR.

## Shipped
- The 26 string-path patches in `tests/web/*` now patch the module (or class)
  that holds the name the code under test looks up: `helpers.py`, `test_chat.py`,
  `test_connectors.py`, `test_internal.py`, `test_scheduled.py`, `test_settings.py`,
  `test_skills.py`, `test_threads.py`. No change under `src/`; no test checks anything different.
- `patch_by_string` in `quality/baseline.json` went from 65 uses in 23 files to 39 in 15; the 8 files of this PR are gone from it.

## Not verified
- Windows: the suite ran on Linux only.

## Follow-ups
- The remaining groups of issue #100 (`test_mcp_lg.py` and neighbours, the script/node env tests, the rest).
