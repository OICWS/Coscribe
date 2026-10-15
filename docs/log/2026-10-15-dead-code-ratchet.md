# Dead code is a ratcheted number (shipped)

Why: #232 item 7, guardrail 10 of the assessment (dead code).

## Shipped
- `scripts/ratchet.py` has a ninth metric, `dead_code`: the names `vulture` (confidence 60, "never referenced by name") finds in `src/coscribe`, counted per file and kind. `vulture>=2.14,<3` is a dev dependency.
- The 196 names in the baseline are the whitelist. Most are reached only by name at run time (a tool the model calls, a route, a Protocol member, a field) and some are dead; the ratchet does not decide which. A name that is new fails `--enforce`; deleting a dead one, or using it, makes the number better and `--update` shrinks the list.
- Proved by breaking: an unreferenced function appended to `conversation/turn_text.py` makes `--enforce` print `WORSE dead_code: new ... _planted_dead_function` and exit 1; removing it exits 0. The two versions of Python in use (3.11 in CI, 3.13 here) list the same 196 names. `tests/test_ratchet.py` covers the metric on a small package.

## Not verified
- Windows: the keys use forward slashes, but the list was only generated on Linux.

## Follow-ups
- Go through the 196 and delete the dead ones; each one removed is a smaller baseline (not scheduled).
