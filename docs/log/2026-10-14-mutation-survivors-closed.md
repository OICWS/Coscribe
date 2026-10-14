# The mutation survivors of the seven modules are closed (shipped)

Why: #165 asked for the survivors of the nightly mutation run to be killed or explained, module by module (#221 to #227). All seven are done, tests only.

## Shipped
Caught mutants per module, `python scripts/mutation.py run KEY --out DIR` (mutmut 3.8.0, Linux), before from the issue and after from the run on the merged tests:

| Module | Mutants | Caught before | Caught after | Left, all equivalent | Log |
|---|---|---|---|---|---|
| `runtime/secrets.py` | 82 | 71 | 82 | 0 | `2026-10-14-mutation-secrets.md` |
| `runtime/secret_store.py` | 444 | 297 | 425 | 19 | `2026-10-14-mutation-secret-store.md` |
| `runtime_lg/exec_policy.py` | 130 | 80 | 127 | 3 | `2026-10-14-mutation-exec-policy.md` |
| `tools/script_guard.py` | 105 | 63 | 103 | 2 | `2026-10-14-mutation-script-guard.md` |
| `code_runtime/permissions.py` | 66 | 45 | 62 | 4 | `2026-10-14-mutation-code-permissions.md` |
| `workflows/spec.py` | 352 | 271 | 347 | 5 | `2026-10-14-mutation-workflow-spec.md` |
| `tools/_xlsx_lookup_formulas.py` | 758 | 529 | 718 | 40 | `2026-10-14-mutation-xlsx-lookup-formulas.md` |
| Total | 1937 | 1356 | 1864 | 73 | |

No change under `src/` in any of the seven pull requests. Every mutant still alive is listed in its module's log entry with the reason its behaviour cannot differ; the common kinds are a changed codec-name case, `typing.cast` arguments, a default that equals the removed value, and a branch that no input reaches.

## Not verified
- Windows: mutmut runs on Linux only, so the encoding tests check the `encoding` argument, not a locale difference.

## Follow-ups
- The nightly mutation run keeps these modules; a new survivor there means a new gap, to be fixed in the pull request that caused it.
