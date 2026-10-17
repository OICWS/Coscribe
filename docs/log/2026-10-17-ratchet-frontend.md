# Frontend file and function sizes in the ratchet (shipped)

Why: #348 item 6. The ratchet read Python only, so `App.tsx` and the 53 long frontend functions could grow unseen.

## Shipped
- `office-agent/scripts/ts_sizes.mjs` parses `frontend/src` and `office-agent-desktop/src` with the
  frontend's own `typescript` and prints the line count of each file and each named function.
- `scripts/ratchet.py` gains `frontend_file_lines` (files over 800 lines) and
  `frontend_long_functions` (named functions over 100 lines), with the Python limits. Names are
  `office-agent/frontend/src/...::Component`, and a repeated name in one file gets `#2`.
- `quality/baseline.json`: 4 files and 53 functions are the starting point, `App.tsx` (1,124) and
  `App` (1,035) the largest. `check.sh --enforce` now fails when one grows or a new one appears.
- `tests/test_ratchet.py` lists a long function and file in a temporary TypeScript tree by name.

## Not verified
- Only the Linux CI job ran it; the script reads files with `/` and `\n`, and no Windows machine was tried.

## Follow-ups
- `knip` for unused exports and the rule that `lib/` and `types/` do not import components.
