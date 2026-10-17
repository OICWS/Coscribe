# `scripts/slice.py` and the discovery protocol (partly shipped)

Why: issue #348 item 3. A session should find its slice from a path instead of reading around.

## Shipped
- `office-agent/scripts/slice.py <path>` prints the file's component (longest match in
  `components.toml`), its card, the interface (`__all__` read from source), the tests (those the
  card names, those that name the module, a frontend file's sibling `*.test.*`) and the modules
  that import it, then the size of the slice in files and tokens (4 characters a token) against
  the 15 files and 150k tokens of the budget. It exits 3 when a slice is over budget.
- The root `AGENTS.md` "Read this first (about 15 minutes)" is replaced by "How to find your
  slice": the map, the card, the interface, then the implementation of one component; no
  whole-file reads over 1,500 lines; history only by `grep`.
- `tests/test_slice.py` covers the longest-match rule, a docx and a frontend path and a path
  outside every component.

## Not verified
- Fresh sessions making three real changes were not run; `docs/metrics/2026-10-17-slice-budget.md` holds the static slice sizes instead (docx 7 files / 28k tokens, web 8 / 18k, frontend 1 / 12.5k with no card).
- Token counts are an estimate from file size, not a tokenizer.

## Follow-ups
- Measure three sample changes made by fresh sessions (#348 item 3); the frontend slice has no card yet.
