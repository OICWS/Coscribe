# runtime_lg has a module card (shipped)

Why: `runtime_lg` is the package an AI session reads most before changing anything, 18 modules and a 3.6k-line README (#232, item 4; part of #166).

## Shipped
- `office-agent/src/coscribe/runtime_lg/AGENTS.md` (60 lines, the fixed headings) and its `CLAUDE.md` import: purpose by module, the 41 exported names grouped, the four packages it depends on, and the invariants (the fixed tool list, the sign-in in the user's own browser, approvals not being a sandbox, the layer it sits in, the two invariant paths). `tests/test_module_cards.py` already checks the headings, that the interface lists everything in `__all__` and that "Depends on" equals the real imports; it passes with the new card.
- No code changed.

## Not verified
- The two "Verify by hand" items (a hosted connector's sign-in with a real account, the prompt cache holding in a long real conversation) were not run.

## Follow-ups
- Cards for `tools`, `web` and the small packages, one per pull request (#232, item 4).
