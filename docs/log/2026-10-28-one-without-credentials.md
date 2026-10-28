# One copy of the proxy's credential stripping (shipped)

Why: #668, #670 and #672 each carried the same `without_credentials` (take a proxy URL's
`user:password@` out), and two copies of a security helper drift.

## Shipped
- `tools/exec/env_allowlist.py` and `code_runtime/launch.py` use `runtime.without_credentials`
  (`runtime/proxy.py`) instead of their own copies; its tests are in `tests/test_proxy.py`.
- `docs/plan.md` item 6: #666 and part 2 of #667 shipped.

## Not verified
- Nothing beyond the existing tests: the three copies were the same code.
