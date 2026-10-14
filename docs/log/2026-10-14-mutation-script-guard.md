# Mutation survivors of `tools/script_guard.py` killed or explained (shipped)

Why: the nightly mutation run left 36 survivors, 6 of them in code no test reached (#225, part of #165).

## Shipped
- `tests/test_script_guard.py`: the wrapper and its config are written beside the script with the documented names and content, as UTF-8; probing a Node runs each flag set in turn with the documented command, timeout and capture, stops at the first that starts, and gives `None` when none starts or the Node cannot run; `node_guard_args` probes each Node once, caches a negative answer, and allows writes only to the roots given; the refusal note and the locked-file note are compared word for word.
- `python scripts/mutation.py run script_guard --out DIR` (mutmut 3.8.0, Linux): before, 63 of 105 caught (the numbers in #225); after, `{"mutants": 105, "killed": 103, "survived": 2, "timeout": 0, "no_tests": 0}`. No change under `src/`.

| Group | Mutants | Why the behaviour cannot differ |
|---|---|---|
| `"utf-8"` to `"UTF-8"` (`write_python_wrapper`, twice) | 2 | codec names are case-insensitive |

## Not verified
- Windows and a real older Node: the Node probe is tested with a scripted `subprocess.run`, so which Node versions accept which flags is not exercised here. mutmut forks and runs on Linux only.

## Follow-ups
- #165 closes with the per-module numbers once the other mutation issues are done.
