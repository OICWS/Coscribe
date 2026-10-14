# Mutation survivors of `runtime/secrets.py` killed (shipped)

Why: the nightly mutation run left 7 survivors and 4 mutants in code no test reached in `secrets.py` (#222, part of #165).

## Shipped
- `tests/test_secrets.py`: the exact message when the keyring package is absent and when a ref is missing from the keychain; `keychain_backend_usable` for no package, the do-nothing backend, a real backend and a probe that raises; `delete_secret` with no keyring package; an empty secret staying empty in `resolve_env_keyring_refs`.
- `scripts/mutation.py run secrets`: 71 of 82 caught before (issue #222), 82 of 82 after. No equivalent mutants left to explain. No change under `src/`.

## Not verified
- Windows: mutmut forks and runs on Linux only; the new tests are plain unit tests.

## Follow-ups
- The other mutation issues (#221, #223 to #227) have their own PRs; #165 closes with the per-module numbers.
