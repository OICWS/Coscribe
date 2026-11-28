# Mutation runs keep their tests in one order (shipped)

Why: the `Mutation of the changes` job failed on pull requests that changed
`runtime_lg/agent.py` (#1111, others before it): mutmut's clean run failed
`test_the_tool_list_never_changes_and_a_found_tool_runs_under_its_real_name` with
`'' == 'done'`, and the same tests passed outside mutmut.

## Shipped
- The cause was a test, not mutmut: `test_deferred_and_approval_gated_tool_still_pauses_once_discovered`
  called `tool_metadata(write_pptx_chart, risk_category="WRITE_LOCAL")` on the module's shared
  function, so any later test that used `write_pptx_chart` stopped for approval. mutmut gives
  pytest its tests as a set of strings, so their order changes with each run's string hash, and
  only some runs put the two tests in that order. #1102 already gave that test its own local
  function, so `main` passes.
- `scripts/mutation.py` now runs mutmut with `PYTHONHASHSEED=0`, so its tests run in the same
  order every time: a test that leaks state fails on every run, and the same command reproduces it.
- Checked on `main`: the agent.py run from #1111's diff gives 128 mutants, 102 killed, twice in
  a row; its 110 tests in mutmut's copy pass in 40 shuffled orders.

## Not verified
- Only on Linux, where mutmut runs; the product is not affected.
