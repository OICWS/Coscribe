# Security review pack

What the quarterly human security review (decision 0009) reads. Every row names the code, the
decision that explains it and the test that guards it, so the reviewer can start from the test
and see what would break. Facts here were checked against the code on 2026-10-17; a row whose test
is missing says so.

## 1. Invariant paths

`CODEOWNERS` lists these; a change to one needs an independent review that is posted on the PR.

| Path | What it holds | Guarded by |
|---|---|---|
| `office-agent/src/coscribe/runtime/secrets.py`, `secret_store.py` | keychain access, secret names and allowed hosts | `tests/test_secrets.py`, `tests/test_secret_store.py`, `tests/test_secret_redaction_properties.py`, `tests/test_connector_secrets.py`; mutation testing (`.github/workflows/mutation.yml`, `scripts/mutation.py`) |
| `office-agent/src/coscribe/runtime_lg/tool_deferral.py` | the fixed, cached tool list and `search_tools` / `use_tool` | `tests/test_tool_deferral.py`, `tests/test_tool_schema_snapshot.py` |
| `office-agent/src/coscribe/runtime_lg/mcp_oauth.py` | connector sign-in, the loopback callback | `tests/web/test_connectors.py` (the OAuth flows against `tests/oauth_mcp_server.py`) |
| `office-agent/src/coscribe/code_runtime/permissions.py` | what Codex may do without asking | `tests/test_code_permissions.py` |
| `office-agent/src/coscribe/coordinator.py` | the instructions and the core tool names | `tests/test_tool_schema_snapshot.py` |
| anything that opens a listener | see section 4 | `tests/test_web_routes.py` |

## 2. The approval decision

`office-agent/src/coscribe/conversation/approvals.py` decides, for each tool call, whether it
runs, is refused or waits for a person. The precedence is one table, `ROWS` in
`tests/test_approval_decisions.py`, and every row is run against the real decision code. In order:

1. A stop request refuses everything and logs nothing.
2. A hook veto (`PreToolUse`) refuses, even a tool that is not gated, a pre-approved one or a run
   that skips approval.
3. A tool that is not gated runs, in plan mode too.
4. Plan mode refuses every gated call; standing approvals and Accept Edits do not lift it.
5. An exec policy rule `forbidden` refuses a script before plan mode is read; `allow` approves a
   script (not in plan mode) and works unattended; `prompt` and rules for other tools change nothing.
6. A standing approval (`preapproved`) approves any risk tier and is logged as such.
7. Accept Edits approves local writes only; scripts and external actions still ask.
8. A scheduled run's approval mode: `skip` approves every tier, `auto` approves local writes and
   still asks for scripts; an unattended run that would ask refuses instead of waiting.
9. Anything else asks the person, and refuses when nobody can answer.

Every decision is written to the audit log (`runtime_lg/audit.py`, `tests/test_audit_log.py`) with
its reason. Auto mode adds a reviewer model (`runtime_lg/auto_review.py`); its three-blocks-in-a-row
rule falls back to asking. Risk tiers (`READ`, `WRITE_LOCAL`, `EXEC`, `EXTERNAL`) come from tool
metadata, so a new tool without one is not gated: check this on every new tool.

## 3. How secrets flow

Decision 0003. A secret is a name, a value in the OS keychain and the hosts it may be sent to.

- Stored: only in the keychain; no keychain means no save (`runtime/secret_store.py`).
- Used: the model writes `{{secret:NAME}}` in `http_request`; the value is substituted after the
  call, for an allowed host, over https, without following redirects
  (`tools/web/http_request.py`, `tests/test_http_request.py`).
- Hidden: every stored value and its common encodings are blanked from every tool result at the
  outermost middleware, before the model, transcript, UI or audit log read it
  (`tests/test_secret_redaction_properties.py`).
- Never given: scripts and Codex receive no value; `http_request` is not given to the code module.
- Names and hosts reach the model through `list_secrets`, never a tool schema or the system prompt.

The promise is the narrow one in `SECURITY.md`: the model cannot see a value. Code that digs, an
allowed host that echoes a value back, and encodings the redaction does not know are outside it.

## 4. Listeners and who may reach them

| Listener | Binds | Opened by | Check |
|---|---|---|---|
| The web server and the chat and browser sockets | `127.0.0.1`, port 8000 by default (the desktop shell picks a free port, `office-agent-desktop/src/main/paths.ts`) | `web/app.py` | `tests/test_web_routes.py` pins the routes; `Host` and `Origin` must name this machine (`web/local_guard.py`, `tests/web/test_local_guard.py`); a WebSocket and any request that changes state also carry the launch token (`tests/web/test_launch_token.py`) |
| The connector sign-in callback | `localhost`, one fixed port, only during a sign-in | `runtime_lg/mcp_oauth.py` | the callback tests in `tests/web/test_connectors.py` |
| The in-app browser's debugging port | loopback, a port Chromium picks (`--remote-debugging-port=0`) | `web/browser_panel.py` | `tests/test_browser_panel.py` |
| The desktop shell's background-event stream | the same server, `/internal/` | `web/routes/internal.py` | no auth beyond being reachable, as the file says |

Every request and WebSocket handshake passes `LocalOnlyGuard` (`web/local_guard.py`) first. The
`Host` must be `localhost`, `127.0.0.1` or `::1` (or a name in `COSCRIBE_ALLOWED_HOSTS`, which
`coscribe-web` fills from a non-loopback `--host`; names only, ports are ignored), which stops a rebound hostname. A browser-sent
`Origin` must name one of those hosts on any port, which stops a cross-site page; a request without
an `Origin` (the CLI, the desktop shell, scripts) passes, unless the browser says `Sec-Fetch-Site: cross-site`. Odd forms (userinfo, backslashes, a bad port, a second `Host` or `Origin` header) are refused. A refused handshake is closed with 1008
before it is accepted.

A page served from *another loopback port* passes both checks (`localhost:5173` is loopback), so each
launch also makes a random token (`COSCRIBE_LAUNCH_TOKEN` fixes one for a dev setup). The app's own
page is served with it in a `<meta>`; its scripts send it as `x-coscribe-token` on every request that
is not a read, and as `?token=` on a WebSocket, which cannot set a header. A page on another port
cannot read the token (no CORS headers) and cannot send the header without a preflight the app
refuses. Reads need no token, so images, downloads and iframes keep working. Some GETs do start things (a
session and its `SessionStart` hooks, a package environment, `npm view`), so a browser GET that
says `Sec-Fetch-Site: same-site` or `cross-site` is refused; a browser that sends no such header
is not covered. `test_every_get_route_has_been_read_for_side_effects` also fails on any GET route
not read by a person. The one GET that does change state is the connector
sign-in callback, which is a cross-site navigation by nature and carries the sign-in's own `state`.
The desktop app's browser-host routes keep their own token. The first-run setup page has no token
(it runs once, before any data exists). Not covered: any local process, which can read the page, or
send whatever headers it likes.

Text the model reads (files, pages, messages from other conversations) is covered in
[`prompt-injection.md`](prompt-injection.md).

## 5. The script sandbox and what it leaves out (decisions 0002, 0021, 0022)

- On Windows, where the machine's self-test passed, scripts and Node scripts run in an
  AppContainer holding only the conversation's folders (`tools/exec/isolation.py`,
  `tests/test_isolation.py`, its container tests in the Windows CI job); where it failed,
  scripts are refused unless the person lets the conversation run without isolation, which is
  audited. Command lines run in Codex's Windows sandbox where Settings set it up
  (`tools/exec/command_sandbox.py`, the real sandbox in `tests/test_windows_real.py`); otherwise
  only once the person allowed commands without it, and each is approved.
- Off Windows and outside the container, code runs as the user. The folder guard
  (`tools/exec/script_guard.py`, `tests/test_script_guard.py`) then catches mistakes and is not a
  boundary; the UI and docs must not promise more.
- Gating is by risk tier and permission mode (section 2), plus the exec policy
  (`runtime_lg/exec_policy.py`, `tests/test_exec_policy.py`).
- Workflows are fixed lists of steps: saving is the consent, and a site or folder outside what
  `workflows/permissions.py` lists stops a run (`tests/test_workflow_permissions.py`); no workflow
  step runs an agent, enforced by an import contract (decision 0005, `pyproject.toml`).
- Connector tools are gated by their own permissions (`tools/connector_permissions.py`,
  `tests/test_connector_permissions.py`); a connector signs in once in the user's browser
  (decision 0004) and its tokens go through `runtime/secrets.py`.

## 6. What a reviewer should do with this

1. Run `bash scripts/check.sh` and the tests named above on a clean checkout.
2. Break one row of each section on purpose (flip a precedence in `approvals.py`, let a secret
   through the redaction, drop the host check) and see the named test fail.
3. Read the audit log of a real week (`runtime_lg/audit.py` writes it under the state directory).
4. Decide the open question in section 4 and record the answer in `docs/decisions/`.
