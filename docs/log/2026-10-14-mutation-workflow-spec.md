# Mutation survivors of `workflows/spec.py` killed or explained (shipped)

Why: the nightly mutation run left 81 survivors in the workflow spec's save-time checks and error messages (#226, part of #165).

## Shipped
- `tests/test_workflow_spec.py`: the exact error for a bad name, for each reference a step or condition reads (`inputs`, `when`, condition operands, nested templates), for what a branch or loop leaves readable afterwards, for nesting (3 deep in a loop, a `then` or an `otherwise` arm, not 4), for the 100-step limit counted across nested steps, and for the loop item and `collect` messages; how a problem is joined and numbered (`_workflow_error`); and `_locate`/`_count` against hand-counted step numbers, including blocks inside blocks and a nested `then` arm before `otherwise`.
- `python scripts/mutation.py run workflow_spec --out DIR` (mutmut 3.8.0, Linux): before, 271 of 352 caught (the numbers in #226); after, `{"mutants": 352, "killed": 347, "survived": 5, "timeout": 0, "no_tests": 0}`. No change under `src/`.

| Group | Mutants | Why the behaviour cannot differ |
|---|---|---|
| `split(".", 1)[0]` to `split(".")[0]` or `split(".", 2)[0]`, in `_root` and `_Scope._field` | 4 | only the first piece is read, and the pieces before the first dot are the same whatever the limit |
| `while loc and isinstance(loc[0], int)` to `or` in `_locate` | 1 | the list is never empty or non-integer at the loop test: it starts with an integer and each `continue` follows an integer index |

## Not verified
- Windows: mutmut forks and runs on Linux only. The module is pure, so nothing here depends on the platform.

## Follow-ups
- #165 closes with the per-module numbers once #227 is done.
