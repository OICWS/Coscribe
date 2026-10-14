# Mutation survivors of `runtime/secrets.py` killed (shipped)

Why: the nightly mutation run left 7 survivors and 4 mutants in code no test reached in `secrets.py` (#222, part of #165).

## Shipped
- `tests/test_secrets.py`: the exact message when the keyring package is absent and when a ref is missing from the keychain; `keychain_backend_usable` for no package, the do-nothing backend, a real backend and a probe that raises; `delete_secret` with no keyring package; an empty secret staying empty in `resolve_env_keyring_refs`.
- `python scripts/mutation.py run secrets --out DIR` (mutmut 3.8.0, Linux): before, 71 of 82 caught (the numbers in #222); after, run on this branch's tests, `{"mutants": 82, "killed": 82, "survived": 0, "timeout": 0, "no_tests": 0}`. The first run after the new tests left one survivor (the "missing from the keychain" message, matched only by substring); the exact-message assertion killed it. No equivalent mutants left to explain. No change under `src/`.
- The tests need the real `keyring` package, as the rest of `tests/test_secrets.py` already does.

## Not verified
- Windows: mutmut forks and runs on Linux only; the new tests are plain unit tests.

## Follow-ups
- The other mutation issues (#221, #223 to #227) have their own PRs; #165 closes with the per-module numbers.
