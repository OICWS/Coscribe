# Tests that are safe under `pytest -n 4`; the Windows job tries `-n 4` (shipped; Windows result pending)

Why: CI runs pytest on 4 workers, and some tests took a port in a way another worker could take
first (#176, item 4 of #201).

## Shipped
- `tests/oauth_mcp_server.py`: the test OAuth MCP server binds port 0 and hands that open socket
  to uvicorn (`sockets=`), instead of closing it and binding the number again.
- `tests/test_setup_app.py`: the setup-to-real-app handover test holds one listener on port 0 for
  the whole test and gives each of the two uvicorn servers a copy (`dup()`). It now also checks
  ten fresh connections after the handover all reach the real app, so a setup server that never
  stopped still fails it. If the real app fails to start, the test fails with that error instead
  of waiting.
- `tests/web/test_connectors.py`: the two tests that use the fixed sign-in callback port (47821, a
  product constant) hold an OS file lock in the temp directory while they run, so two workers,
  or two pytest runs on one machine, take turns.
- `.github/workflows/windows.yml`: the Windows test step runs with `-n 4` (pytest-xdist is in the
  `dev` extras).
- Measured: a stress script of 8 processes x 3000 binds saw 10 `EADDRINUSE` with the old
  pick-close-rebind pattern and 0 with bind-0-and-keep. Three pytest processes at once running
  the two callback-port tests, 5 rounds: 4 of 15 failed without the lock, 0 with it.
- Looked at and harmless: the Hypothesis example database (one directory per test, written by
  temp file and rename, and one test never runs on two workers at once); `__pycache__` (Python
  writes `.pyc` atomically); the `/tmp/...` strings in `test_config.py`, `test_mcp_lg.py`,
  `test_chat.py` and `test_images_tool.py` (values that are compared or shown, never written);
  the `tempfile.mkdtemp` directories (unique names); LibreOffice profiles (one per run, claimed by
  an OS file lock in `tools/_office_bins.py`).

## Not verified
- The Windows job with `-n 4`: it runs on the pull request that changes `windows.yml`; keep it or
  go back to serial on that result.

## Follow-ups
- `web/browser_panel.py::_free_port` (product code) picks a port and closes it before Chromium
  binds it: the same gap, outside the tests.
