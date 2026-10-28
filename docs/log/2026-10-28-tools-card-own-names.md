# The `tools` card and `slice.py` list only the names `tools` owns (shipped)

Why: `coscribe.tools.__all__` re-exports 166 names that `exec`, `bookkeeping`, `web` and the office formats already
list on their own cards, so the `tools` card and `slice.py` opened every slice on `tools/` with 220 names
(issue #677, item B; the maintainer's choice was to shorten what a session reads, not to move imports).

## Shipped
- `tools/AGENTS.md` lists the 54 names that belong to `tools` and says the rest are re-exported for older imports
  and live on the sub-component's card.
- `tests/test_module_cards.py`: a name the package re-exports from one of its own sub-packages need not be on the
  parent's card (the sub-component's card must list it, its own test). A name `tools` owns and leaves off the card
  still fails.
- `scripts/slice.py` prints the own names and a count of the re-exported ones; `review_pack.py` uses the own names.

## Not verified
- Nothing was run on Windows; the change is documents, a test and two scripts.

## Follow-ups
- Moving callers to import from the sub-component (the other reading of #677 B) stays undone: it makes `deep_imports`
  and `fan_out` worse today.
