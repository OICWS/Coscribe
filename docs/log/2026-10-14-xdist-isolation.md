# Tests that are safe under `pytest -n 4`; the Windows job tries `-n 4` (partly shipped)

Why: CI runs pytest on 4 workers, and some tests took a port in a way another worker could take
first (#176, item 4 of #201).

## Shipped
- `tests/oauth_mcp_server.py`: the test OAuth MCP server binds port 0 and hands that open socket
  to uvicorn (`sockets=`), instead of closing it and binding the number again.
- `tests/test_setup_app.py`: the setup-to-real-app handover test starts the setup server on a
  port-0 listener the test bound, and the real app then binds the port number itself after the
  setup server let go, as in production. It also checks that ten new connections after the
  handover all reach the real app. If uvicorn cannot bind or start (it calls `sys.exit`), the
  test fails with that reason instead of ending the test run.
- `tests/web/test_connectors.py`: the OAuth connector helper moves the registered-app sign-in
  callback off its fixed product port (47821) to an unused one for every test that uses it
  (`CALLBACK_PORT` and each copy of `APP_REDIRECT_URI` are patched). The busy-port test squats on
  a port it got from port 0 and keeps open. Workers no longer share the fixed port, and a
  coscribe running on the machine no longer breaks these tests. The sign-in test's port is
  picked, not held, since the product binds it itself.
- `.github/workflows/windows.yml`: the Windows test step runs with `-n 4` (pytest-xdist is in the
  `dev` extras), and stays so: the first Windows run with it took 357 s for the tests against
  634 s serially on main's nightly (run 38483391046), and its failures were not caused by the
  workers. Two of its three, `test_file_sizes.py::test_no_new_large_text_file` (`elements.py`
  over 200 KB) and `test_office_golden.py::test_deck_matches_its_golden[icon]`, fail the same way
  in that serial nightly run. The third was the handover test handing a `dup()` of a listener to
  a second server, which Windows' proactor loop refuses (`WinError 87`); the test no longer does.
- Measured: a stress script of 8 processes x 3000 binds saw 10 `EADDRINUSE` with the old
  pick-close-rebind pattern and 0 with bind-0-and-keep. Three pytest processes at once running
  the two callback-port tests, 5 rounds: 4 of 15 failed on the fixed port, 0 with the port
  moved.
- Looked at and harmless: the Hypothesis example database (one directory per test, written by
  temp file and rename, and one test never runs on two workers at once); `__pycache__` (Python
  writes `.pyc` atomically); the `/tmp/...` strings in `test_config.py`, `test_mcp_lg.py`,
  `test_chat.py` and `test_images_tool.py` (values that are compared or shown, never written);
  the `tempfile.mkdtemp` directories (unique names); LibreOffice profiles (one per run, claimed by
  an OS file lock in `tools/_office_bins.py`).

## Not verified
- The reworked handover test on Windows (real app binding the port after the setup server let
  go): it runs on this pull request's next Windows run.

## Follow-ups
- #209: `web/browser_panel.py::_free_port` (product code) picks a port and closes it before
  Chromium binds it: the same gap, outside the tests.
