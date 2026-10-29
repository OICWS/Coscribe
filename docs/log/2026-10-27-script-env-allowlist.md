# Scripts and commands no longer inherit the provider keys (shipped)

Why: `resolve_env_keyring_refs` puts every provider API key into `os.environ` at startup,
because the model SDKs read them there, and the Python and Node script tools, background
scripts and background commands all started their child from a copy of `os.environ`. A script
could print `ANTHROPIC_API_KEY` and so hand it to the model (issue #667). The proxy password of
issue #666 would have gone the same way.

## Shipped
- `tools/exec/env_allowlist.py`: `child_env(extra)` builds a child's environment from a list of
  names (the Windows system and profile folders, `PATH`, `PATHEXT`, `COMSPEC`, `TEMP`, the
  processor names, on POSIX `HOME`, `USER`, `LANG`, `LC_*`, `TZ`; the CA-bundle names a
  TLS-intercepting proxy needs), the proxy addresses (`HTTP_PROXY`, `HTTPS_PROXY`,
  `ALL_PROXY`, `NO_PROXY`, any case) with any `user:password@` taken out, then the
  conversation's own variables over them.
- Used by `run_python_script`, `run_node_script`, `run_background_script`,
  `run_background_command` (in and out of Codex's command sandbox) and the AppContainer
  self-test's probe. `overlay_env` is no longer part of `tools.exec`'s interface.
- Tests: `tests/test_env_allowlist.py`, and one test per tool that sets a fake key and a proxy
  with a password in the server's environment and checks the child sees neither (each fails
  without the change).

## Checked while doing it
- Settings > Secrets values never reach a script's environment: they are substituted only into
  `http_request` and a connector's headers and variables. Tool results, script output
  included, go through `redactor`, which covers those stored secrets but not the provider
  keys; with the keys gone from the environment that gap matters much less.
- Connectors started as local processes already get the `mcp` SDK's own short list plus the
  proxy and CA variables (`runtime_lg/mcp.py`); after #666 that proxy may carry a password,
  which a connector needs to get through an authenticating proxy.
- Programs coscribe itself starts (pip from Settings, LibreOffice, Office through PowerShell,
  the sandbox setup, hooks the person wrote) still get the full environment: they run
  coscribe's or the person's own code, not the model's.

## Assessed: keys as arguments to the model clients (step 3 of #667)
Not done, and not worth it now. With children started from `child_env`, a key in `os.environ`
is readable only by code inside the server process. An isolated script cannot read the server's
memory; an unisolated one runs as the person and can read the keychain or `.env` directly, so
moving the keys out of `os.environ` would not narrow what it reaches. It would mean passing
`api_key=` through every LangChain provider class and through Codex's launch, for no change in
what a script can see.

## Not verified
- A real Windows machine: whether a script or command needs a variable that is not on the list
  (a program that reads `JAVA_HOME`, `GOPATH` or a conda variable now gets it only when the
  person sets it in Edit environment > Variables). The Windows CI job runs the container
  self-test and the command sandbox with the new environment.
- A company proxy that asks for a password: scripts and commands now reach it without one and
  get 407. coscribe's own requests and the model SDKs keep the password.

## Follow-ups
- The code module: Codex hands its own environment, provider keys included, to the commands it
  runs, because its `ignore_default_excludes` defaults to true (checked in Codex's source,
  `codex-rs/config/src/shell_environment_policy.rs`, 2026-10-27). Part 2 of #667.
