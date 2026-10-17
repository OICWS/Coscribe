# The local server refuses a foreign Host or Origin (shipped)

Why: #388 item 1. The server trusted "reachable on loopback", so a page open in the user's browser
could open the chat WebSocket (which answers approvals) and a rebound hostname counted as a local
client. Found while writing the security review pack and reported privately.

## Shipped
- `web/local_guard.py`: an ASGI middleware on the real app and the setup app. `Host` must be
  `localhost`, `127.0.0.1`, `::1` or listed in `COSCRIBE_ALLOWED_HOSTS`; a browser `Origin` must name
  one of those on any port (the Vite dev server on 5173 keeps working); no `Origin` passes. HTTP gets
  403, a WebSocket handshake is closed with 1008 before accept.
- Strict parsing after the independent review: a bad port, userinfo, a backslash, a bare `Origin`, a
  second `Host` or `Origin` header and `Sec-Fetch-Site: cross-site` are refused; the 403 names
  `COSCRIBE_ALLOWED_HOSTS`, which takes names without ports.
- `coscribe-web --host <name>` adds a non-loopback name to the allowed list. A bind to `0.0.0.0` or
  `::` needs `COSCRIBE_ALLOWED_HOSTS` set to the names it is reached by.
- `tests/web/test_local_guard.py` (35 cases, including the real app's HTTP and WebSocket: loopback hosts, rebound and foreign hosts, cross-site POST,
  `null` and `file://` origins, WebSocket open and closed, configured hosts, setup app). `tests/conftest.py`
  allows the TestClient's `testserver`; `tests/test_setup_app.py` uses a loopback base URL.
- `docs/security/review-pack.md` section 4 states the new rule and what it does not cover.

## Not verified
- The desktop app and the packaged installer on Windows: the shell loads `http://127.0.0.1:<port>` and
  its main process sends no `Origin`, read from `office-agent-desktop/src/main/mainWindow.ts` and
  `sidecar.ts`, not run.
- The Vite dev server proxy and the Playwright specs against a live backend (CI's e2e job covers them).
- An independent review was done on the first head (a comment review on the PR); its blocking item,
  a test of the real app, is added.

## Follow-ups
- Another page served from a loopback port still passes the `Origin` check; a per-launch token would
  close that and is not part of this change.
