# `runtime` has a package card (shipped)

Why: #166, structure-period step 7. A reader should get `runtime` from its card instead of nine source files.

## Shipped
- `runtime/AGENTS.md` (+ `CLAUDE.md`): purpose, public interface, dependencies, the invariants that a test or a lint checks, tests, what to verify by hand. `tests/test_module_cards.py` now covers it.
- `runtime/__init__.py` exports the secret-store names that callers already imported from a submodule (`SecretStore`, `redactor`, `host_allowed`, `placeholders_in`, `substitute`, `MIN_VALUE`, `KeychainUnavailable`, `keychain_available`).
- About 60 callers in `src`, `tests` and `scripts` import those names from `coscribe.runtime` instead of a submodule; no behaviour change. `deep_imports` in the ratchet drops accordingly.

## Not verified
- The Windows Credential Manager and a hook under the Windows shell (the card lists them under "Verify by hand").

## Follow-ups
- `code_runtime` and `conversation` cards follow in their own PRs (#166).
