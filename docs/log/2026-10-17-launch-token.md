# The local server needs a per-launch token for sockets and writes (shipped)

Why: #402 item 1, the follow-up of #390. The Host and Origin checks let a page served from another
loopback port through (`localhost:5173` is loopback), and that page could open the chat WebSocket,
which answers approvals.

## Shipped
- `web/local_guard.py`: each launch makes a token (`COSCRIBE_LAUNCH_TOKEN` fixes one). A WebSocket
  handshake (`?token=` or the header) and any request that is not GET/HEAD/OPTIONS must carry it.
  The desktop app's browser-host routes keep their own token. `/` is served with the token in a
  `<meta name="coscribe-token">` and `Cache-Control: no-store`.
- Frontend: `lib/launchToken.ts` adds the header to same-origin writes and the token to both sockets;
  Vite adds it to what it proxies when `COSCRIBE_LAUNCH_TOKEN` is set (the e2e workflow does).
- The GET audit: all 52 GET routes read for a side effect. None changes state except the connector
  sign-in callback (bound to the sign-in's own `state`); `npm-latest-version` runs `npm view` for a
  validated package name and changes nothing. `test_every_get_route_has_been_read_for_side_effects`
  fails on a GET route nobody listed.
- The connector sign-in callback is a cross-site navigation by nature (`Sec-Fetch-Site: cross-site`),
  which #390 would have refused in a real browser; it is now the one GET allowed to arrive that way.
- Tests: `tests/web/test_launch_token.py` (10), `lib/launchToken.test.ts` (4); `TokenClient` in the
  web test helpers sends the token on every request and socket.

## Not verified
- The desktop app and a real browser on Windows (the page gets the token from its own `/`; the shell
  sends no writes of its own except the browser-host ones, which keep their token).
- A real connector sign-in through the callback (no identity provider here).
- The e2e workflow with the token (it runs on this PR because the PR changes the workflow).

## Follow-ups
- The first-run setup page has no token.
- Reads need no token, so a cross-site `<img>` can still trigger a GET; that is safe only while the
  audit holds.
