# Who uses the names of `coscribe.tools`: a script and a measurement (shipped)

Why: `coscribe.tools` has 230 names in one `__all__`, so the card and `slice.py` open a
session's slice with a list that long (issue #677, item A, record 0009). Splitting it needs to
know who uses what first.

## Shipped
- `scripts/tools_interface_usage.py`: per name, the sub-component it comes from, the
  components of `src` that import it and the test files that do.
- `docs/metrics/2026-10-28-tools-interface-usage.md`: the table, with the 10 names nothing uses
  and the cost of B (a sub-component import counts as deep in `deep_imports` today).

## Not verified
- Dynamic uses (`getattr`, strings) are not read.

## Follow-ups
- Drop the 10 unused names and add a ratchet number for the interface's size (next PR).
- B: teach `deep_imports` the declared sub-components, then one PR per sub-component.
