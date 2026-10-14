# providers has a module card; the card list in office-agent/CLAUDE.md is complete (shipped)

Why: last card of #232 item 4 (part of #166). `providers` was the only package left without one.

## Shipped
- `providers/AGENTS.md` and `CLAUDE.md`, and `__all__ = ["GeminiProvider"]` in `providers/__init__.py` (the card test compares against it). Importing `coscribe.providers` now imports `gemini_provider`, which needs only `aisuite`.
- `office-agent/CLAUDE.md` now lists every package with a card.
- `cli`, `config`, `coordinator` and `needs_permission` are single modules, not packages. `test_module_cards.py` only reads `*/AGENTS.md`, so they get no card; turning them into packages is out of scope.

## Not verified
- The "Verify by hand" item (a real Gemini key) was not run.

## Follow-ups
- None for item 4.
