# `code_runtime` has a package card (shipped)

Why: #166, structure-period step 7. Second of the three package cards (`runtime` is #183).

## Shipped
- `code_runtime/AGENTS.md` (+ `CLAUDE.md`); `tests/test_module_cards.py` covers it. The card test now also accepts the bare `coscribe` package in "Depends on", because `launch.py` reads `__version__` from it.
- `code_runtime/__init__.py` exports what other packages import (`CodeService`, `code_service`, `CodePermissions`, `CodexThread`, ...); callers in `web`, `runtime_lg`, `conversation` and two tests import from the package. Import lines only. `code_runtime/permissions.py` (an invariant path) is not changed.

## Not verified
- The whole module on real Windows (listed on the card under "Verify by hand"); no test starts a real Codex.

## Follow-ups
- The `conversation` card (#166) is last.
