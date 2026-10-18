# The workflow spec moves below tools (shipped)

Why: batch 10 item 4 (#425). `tools/bookkeeping/scheduled_tasks.py` imported the spec from
`workflows`, which sits above `tools`; the layers contract carried an ignore for it.

## Shipped
- `workflows/spec.py` and `refs.py` are now the package `coscribe.workflow_spec` (card, `__all__`
  of 19 names, protected contract generated from `components.toml`), in the lowest layer next to
  `runtime`. `tools`, `workflows` and the tests import from it; `workflows` still re-exports the
  definition names, so `web` and `conversation` are unchanged.
- The layers contract has no `ignore_imports` left; the forbidden-agents contract lists
  `workflow_spec` as a source, so the spec still cannot reach the agent runtimes.
- Checked by breaking: an upward `from ...workflows import ...` in `tools/bookkeeping/scheduled_tasks.py`
  breaks two contracts (layers, and tools without LangChain); removed, 21 kept / 0 broken.
- Ratchet: `deep_imports` 3 to 2, `engine.py` 901 to 898 lines; dead-code keys renamed.

## Not verified
- Windows run of the moved tests (CI's Windows job and the nightly cover it).
