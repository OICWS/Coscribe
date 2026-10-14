# Mutation survivors of `runtime_lg/exec_policy.py` killed or explained (shipped)

Why: the nightly mutation run left 50 survivors in `_load_exec_policy` (#223, part of #165).

## Shipped
- `tests/test_exec_policy.py`: the exact warning for an unparseable file (with its traceback), a file that is not a rules object, and each kind of bad rule (not an object, no pattern, an empty or non-text pattern, an invalid decision, an invalid regex), by position and path; the good rules around bad ones still load; an empty pattern is skipped instead of matching every script; a rule without a decision prompts and shadows later rules; a justification that is not text is dropped; the file is read as UTF-8.
- `python scripts/mutation.py run exec_policy --out DIR` (mutmut 3.8.0, Linux): before, 80 of 130 caught (the numbers in #223); after, `{"mutants": 130, "killed": 127, "survived": 3, "timeout": 0, "no_tests": 0}`. No change under `src/`.

| Group | Mutants | Why the behaviour cannot differ |
|---|---|---|
| `"utf-8"` to `"UTF-8"` | 1 | codec names are case-insensitive |
| `entry.get("justification", "")` default changed to `None` or removed | 2 | a missing or `None` justification is not text, so the next line turns it into `""` either way |

## Not verified
- Windows: mutmut forks and runs on Linux only. The UTF-8 test checks the `encoding` argument, since a Linux run cannot show a locale difference.

## Follow-ups
- #165 closes with the per-module numbers once the other mutation issues are done.
