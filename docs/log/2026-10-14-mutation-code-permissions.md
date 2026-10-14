# Mutation survivors of `code_runtime/permissions.py` killed or explained (shipped)

Why: the nightly mutation run left 21 survivors in `CodePermissions` (#224, part of #165).

## Shipped
- `tests/test_code_permissions.py` (new; `MODULES["code_permissions"]` in `scripts/mutation.py` now selects it too): a missing, unparseable or non-object file reads as "ask"; stored values are kept, unknown values and stray keys are ignored; an unknown action's policy is "ask"; `update` merges, creates a nested state folder and writes the indented JSON; a refused update says what it expected, lists each problem, and writes nothing; the file is read and written as UTF-8.
- `python scripts/mutation.py run code_permissions --out DIR` (mutmut 3.8.0, Linux): before, 45 of 66 caught (the numbers in #224); after, `{"mutants": 66, "killed": 62, "survived": 4, "timeout": 0, "no_tests": 0}`. No change under `src/`.

| Group | Mutants | Why the behaviour cannot differ |
|---|---|---|
| `"utf-8"` to `"UTF-8"` (`load`, `update`) | 2 | codec names are case-insensitive |
| `cast(Policy, ...)` to `cast(None, ...)` (`load`, `update`) | 2 | `typing.cast` returns its argument unchanged at run time; it only informs the type checker |

## Not verified
- Windows: mutmut forks and runs on Linux only. The UTF-8 test checks the `encoding` argument, since a Linux run cannot show a locale difference.

## Follow-ups
- #165 closes with the per-module numbers once the other mutation issues are done.
