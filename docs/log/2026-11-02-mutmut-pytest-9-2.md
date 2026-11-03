# Nightly mutation runs again with pytest 9.2 (shipped)

Why: from 2026-10-27 every nightly Mutation job failed after its first test. pytest 9.2.0 (released that day) has no `Item._nodeid`, which mutmut 3.8.0's harness read, so each module stopped with `AttributeError` and no mutant was tested for a week.

## Shipped
- `.github/workflows/mutation.yml` installs mutmut 3.8.1, whose harness reads `item.nodeid`.
- Checked here with pytest 9.2.0 on `code_permissions`: mutmut 3.8.0 fails the same way as the nightly; 3.8.1 gives `{"mutants": 66, "killed": 62, "survived": 4}`, the numbers of 2026-10-14.

## Not verified
- The other six modules; only the nightly run shows them.
