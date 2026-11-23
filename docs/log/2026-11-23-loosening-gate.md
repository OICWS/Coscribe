# Loosening a limit needs the maintainer's label; the core and each component have a size budget (shipped)

Why: decision 0009 says only a human may loosen a ratchet, but `ratchet.py --update
--accept-worse` is open to any session, code-owner review is not required (0007, one maintainer),
and the core budget of about 100k lines was written down without anything checking it. Part of
#1051, step 2.

## Shipped
- `scripts/loosened.py` and the `loosened` job of `pr-text.yml`: a pull request fails when, from
  its merge base, a number in `quality/baseline.json` got worse, a budget grew, a component left
  the core, an `ignore_imports` entry was added (`components.toml`, `pyproject.toml`), the
  coverage floor went down, or `pyproject.toml` turned a ruff, mypy or coverage check off for
  some code, unless its description has a `Loosened:` line and it carries the
  `loosening-approved` label. Sessions share the maintainer's account, so the label records the
  maintainer's decision; it is not an identity check. `AGENTS.md` says a session never adds it.
- `quality/budgets.json`: the core at most 100,000 lines and each component at most 20,000 own
  lines (without the components nested in it and vendored code), checked by `ratchet.py
  --enforce` in `check.sh`. `components.toml` marks the core (`core = true`): cli, web,
  conversation, coordinator, runtime_lg, code_runtime, runtime, runtime.models, config,
  thread_paths, needs_permission. Today: core 35,746 lines; the largest component is
  `tools.office.pptx` at 15,259.

## Not verified
- The `loosened` job on a real pull request with the label added and removed: the script was
  run against commits here, the workflow only once it runs on this pull request.

## Follow-ups
- The maintainer makes `loosened` a required check in the ruleset and creates the
  `loosening-approved` label.
