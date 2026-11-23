# The frontend's features are components, entered through their index (shipped)

Why: the frontend is 68k lines and was one component with one rule (`lib/` and `types/` don't
import `components/`), while the Python side has a public interface per package, import
contracts and a card. At 1M lines a session must be able to change one feature without reading
the others. Part of #1051, step 4.

## Shipped
- `components.toml`: the eleven folders of `frontend/src/components/` are components
  (`frontend.artifacts`, `chatlog`, `design`, `doc`, `dock`, `environment`, `files`, `sessions`,
  `settings`, `slides`, `workflow`), each with a `CODEOWNERS` line and a row in
  `docs/components.md`; `slice.py` now names the feature a frontend file belongs to.
- `frontend_feature_imports` in `scripts/ratchet.py`: an import from outside a feature into one
  of its files other than its `index.ts` (static, `export ... from` and dynamic `import()`),
  counted per pair. Today 106 such imports over 35 pairs, the largest the loose components into
  `workflow` (16) and `chatlog` (9), and `doc` into `slides` (8). The baseline holds them; a new
  pair or a larger count fails `check.sh`.
- `frontend/AGENTS.md` says how to use another feature: export it from that feature's
  `index.ts`.

## Not verified
- Nothing in the UI changed; no feature has an `index.ts` yet, so every count is today's debt.

## Follow-ups
- Give each feature an `index.ts` and move its users onto it, largest pairs first.
- Size budgets for the frontend features once `quality/budgets.json` (#1052) is on `main`.
