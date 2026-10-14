# tools has a module card (shipped)

Why: `tools` is the largest package (48 modules, 72 exported names) and the one most sessions change (#232, item 4; part of #166).

## Shipped
- `office-agent/src/coscribe/tools/AGENTS.md` (60 lines, the fixed headings) and its `CLAUDE.md` import: what each group of modules owns, the 72 exported names by group, the three packages it depends on, and the invariants (no LangChain, the fixed tool schemas, risk tiers, workspace scoping and the folder guard that is not a boundary, secrets the model never sees, whole-page office sources). `tests/test_module_cards.py` checks the headings, `__all__` and the real imports; it passes.
- No code changed.

## Not verified
- The three "Verify by hand" items (output opened in the real Office on Windows, a script run with no Python or Node, the browser tools on a real page) were not run.

## Follow-ups
- Cards for `web` and the small packages; `web`, `providers`, `config` and `cli` have no `__all__` yet, which the card test needs first (#232, item 4).
