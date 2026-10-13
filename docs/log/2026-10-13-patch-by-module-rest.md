# The remaining tests patch module objects, not string paths (shipped)

Why: last part of issue #100. A string-path `monkeypatch.setattr("coscribe.x.y.name", ...)` keeps passing when `name` moves, and the planned splits of the large modules will move many of them.

## Shipped
- The 20 string-path patches in `tests/conftest.py` (2), `test_browser_panel.py` (4), `test_cli.py` (4), `test_code_agent.py` (3), `test_code_runtime_install.py` (1), `test_prompt_cache.py` (1), `test_scheduled_tasks_resume.py` (4) and `test_selfwake_resume.py` (1) now patch the module as an object. No change under `src/`; no test checks anything different.
- `patch_by_string` in `quality/baseline.json` is empty; no use was left as impossible.

## Not verified
- Windows: ran on Linux only.

## Follow-ups
- None for this issue. Patches that did not matter to their test are listed in the pull request.
