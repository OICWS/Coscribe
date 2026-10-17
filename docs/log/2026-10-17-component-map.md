# Component map: `components.toml` and what is generated from it (partly shipped)

Why: issue #348 item 1. Phase 2 of decision 0009 makes the component the unit a session works
in; the map is the list that cards, owners and later import contracts hang on.

## Shipped
- `components.toml`: one entry per top-level package and single module of `coscribe`, plus the
  frontend and the desktop shell (name, path, layer, owner, card).
- `office-agent/scripts/gen_components.py` writes `docs/components.md` and a generated block at
  the top of `.github/CODEOWNERS` (above the invariant paths, because the last match wins);
  `--check` is in `scripts/check.sh`.
- `tests/test_components_map.py`: fails when either generated file is stale, a path or card
  does not exist, a package card has no component, or a top-level package is missing. Each check
  was shown to fail by breaking the input (a stale line in `docs/components.md`, a wrong card path).
- Nothing is cut yet: `tools` is still one component. This is part 1.

## Not verified
- The code-owner ruleset is informational today (`require_code_owner_review` is off), so the
  new CODEOWNERS lines have no effect on merging; GitHub's own CODEOWNERS syntax check was not run.
- The frontend build could not run in the cloud container (`vitest` missing in `node_modules`);
  this change touches no frontend file.

## Follow-ups
- Cut `tools` into components one PR at a time (`tools.office.pptx`, `.docx`, `.xlsx`, `.pdf`,
  `tools.exec`, `tools.web`, bookkeeping), each with `__all__` and a card; extend
  `tests/test_module_cards.py` to sub-packages (#348 item 1).
