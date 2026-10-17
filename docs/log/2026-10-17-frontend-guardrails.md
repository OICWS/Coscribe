# knip and the lib/types import rule (shipped)

Why: #348 item 6, second half. Nothing found unused exports in the frontend or stopped `lib/` and `types/` from reaching up into the components.

## Shipped
- `frontend/knip.json` and the `knip` dev dependency. `ratchet.py` gains `frontend_unused_exports`: the
  exports, types and files nothing imports, per file (`src/types/wire.gen.ts` is generated and ignored).
  18 files with 36 findings are the baseline; a new one or a bigger count fails `check.sh --enforce`.
- `frontend/.oxlintrc.json`: `no-restricted-imports` makes `src/lib/**` and `src/types/**` an error
  when they import `components/`. Nothing imported it before, so no code moved. A probe file in `lib/`
  importing a component failed `oxlint`.
- `tests/test_ratchet.py` lists an unused export of a temporary project by file.

## Not verified
- Only the Linux CI job ran knip; no Windows run.

## Follow-ups
- The `src/features/` cut of `App.tsx` is proposed on #348, not made (the viewer is in `App.tsx`, #346).
