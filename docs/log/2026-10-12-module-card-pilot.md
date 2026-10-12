# A card and a public interface for `workflows` (shipped, pilot)

Why: a session that changes one package should read a short card instead of the source, and
other packages should import from the package, not from its submodules (step 7 of the
assessment). `workflows` is small (2.5k lines) and well covered, so it is the trial.

## Shipped
- `workflows/__init__.py` exports what other packages use (`__all__`, 21 names); eight files
  in `web`, `runtime_lg` and `conversation` import from it. The deep-import baseline drops
  from 168 to 154, and three line counts shrink by 2 to 3 lines.
- `workflows/AGENTS.md` (the card, 7 fixed headings) and `workflows/CLAUDE.md`
  (`@AGENTS.md`).
- `tests/test_module_cards.py`: every package that has a card has exactly the headings, at
  most 60 lines, every `__all__` name on the card, and a "Depends on" equal to what the
  package imports (grimp). Checked by removing a name from the card.
- The rule in `office-agent/CLAUDE.md`.

## Not verified
- Whether a session works better from the card: judge it on the next change to `workflows`.

## Follow-ups
- `solidify` stays a deep import (it imports `runtime_lg`, which imports `workflows`);
  `tools/scheduled_tasks.py` and `coordinator.py` also stay (an upward import that would
  cycle; the second is an invariant path). Moving `solidify` out of the cycle is its own PR.
- The next package for a card: `runtime` (30 deep imports into `runtime.types`).
- `import-linter` `protected` contracts come after more packages have a card.
