# The commands Codex runs no longer get the provider keys or the proxy password (shipped)

Why: the code module starts `codex app-server` with the server's whole environment, which holds
every provider API key, and Codex hands its environment to the commands it runs. Its own filter
of names holding KEY, SECRET or TOKEN is off by default (`ignore_default_excludes` defaults to
true in `codex-rs/config/src/shell_environment_policy.rs`). Part 2 of issue #667; part 1 (#668)
did the same for the script and command tools.

## Shipped
- `code_runtime/launch.py`'s `config_toml` writes `ignore_default_excludes = false`, excludes
  `COSCRIBE_CODEX_KEY_*` and `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and sets those proxies
  again without their `user:password@`. Codex's own process still gets the full environment:
  it reads its key and the proxy there.
- Checked against the real Codex 0.163.0 Linux binary with `codex sandbox -- env` and fake
  values: before, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and the proxy with its password reached
  the command; after, none of them, the proxy arrives without the password, `NO_PROXY` passes,
  and a conversation variable named `MY_API_KEY` set through the thread's
  `shell_environment_policy` still arrives (Codex applies `set` after the excludes, and a
  thread's `set` merges with the config file's instead of replacing it). Codex matched the
  `HTTPS_PROXY` exclude against `https_proxy` too.
- Tests in `tests/test_code_runtime.py`.

## Not verified
- The Windows build of Codex and its elevated sandbox; Codex's source applies the same policy
  there.
- Variables that hold a secret under another name (`DATABASE_URL` with a password, a tool's own
  proxy variable such as `npm_config_https_proxy`) still reach Codex's commands; the tools'
  allow-list (part 1) does not have this gap.
