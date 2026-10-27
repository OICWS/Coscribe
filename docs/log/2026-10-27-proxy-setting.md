# A proxy setting in Settings: System, Manual or No proxy (shipped)

Why: a proxy could only be set by editing `.env` by hand (`HTTPS_PROXY`, `HTTP_PROXY`,
`NO_PROXY`), and people on a company network can't be asked to do that (issue #666).

## Shipped
- Settings › General › Proxy (`frontend/src/components/settings/ProxySection.tsx`) has its own
  Save and a "Test connection" that tries the unsaved setting. It reaches the default model's
  provider (`api.anthropic.com`, `api.openai.com`, `generativelanguage.googleapis.com`, or a
  custom provider's base URL) and counts any HTTP answer, a 401 too. A 407 or a proxy that
  refuses the tunnel says the user name or password is missing or wrong.
- `GET`/`PUT /api/settings/proxy` and `POST /api/settings/proxy/test`
  (`web/routes/settings/proxy.py`). The setting is written into `.env` as the proxy variables
  every start already loads (both cases, since tools differ), so `cli.py`, `prepare_env` and
  `create_app_lg` need no change:
  - System (the default): writes nothing, so an existing `.env` proxy and Windows' own keep
    working. Switching back to it from Manual or No proxy removes what those wrote.
  - Manual: `HTTP_PROXY`/`HTTPS_PROXY` hold the address with the percent-encoded user name and
    password, `NO_PROXY` holds the "do not use for" list (default `localhost, 127.0.0.1`), and
    `ALL_PROXY` is blanked.
  - No proxy: the proxy variables blank and `NO_PROXY=*`, which httpx, requests and urllib read
    as "bypass every host", so Windows' own proxy is not read either.
- The password: with a user name, the proxy variables hold `__coscribe_keyring__:proxy`, and the
  URL with the password is in the keychain through `env_value_for_storage`, the same helper as
  the provider keys. `resolve_env_keyring_refs` resolves it at start like theirs. With no
  keychain it falls back to the owner-only `.env`, as the provider keys do. It is never returned
  by `GET /api/settings/proxy` or `GET /api/config`. Leaving Manual deletes it.
- `runtime/proxy.py`: the address parser (HTTP only, host and port, no user info in the
  address), `proxy_env`, `try_connection`, `without_credentials`. The browser panel's Chromium
  gets the proxy without credentials, since `--proxy-server` takes only a host and port.
- Checked live: a Manual proxy with a password, saved, then the server restarted. A chat turn
  to the stub model went through a local proxy that demands Basic authentication, and the proxy
  saw the right credentials on every request. The Settings e2e spec saves Manual, checks that
  no response carries the password, and goes back to System.

## Exposure, said plainly
The proxy URL with its password sits in the server's environment, because the model SDKs read
it there. Scripts and commands get the proxy without it (#668, #670: part 1 and part 2 of
#667). Local connectors get it with the password (`runtime_lg/mcp.py` forwards `HTTP(S)_PROXY`
unchanged), because a connector behind an authenticating proxy needs it to connect.

## Not verified
- A real company proxy and Windows: the registry proxy behind "System", Credential Manager
  holding the entry, NTLM or Kerberos proxies (not supported: Basic only, as the SDKs send it).
- Chromium in the browser panel behind a proxy that asks for a password: the flag carries no
  credentials, and nothing answers Chromium's own prompt.

## Follow-ups
- "Use setup script" (PAC) and SOCKS: out of scope by the maintainer's decision on #666.
- One copy of `without_credentials` across `runtime`, `tools/exec` and `code_runtime` once #668
  and #670 are merged.
- `http_request` passes `proxy=configured_proxy()` explicitly, so httpx then ignores `NO_PROXY`
  for it (as it already did before this change).
