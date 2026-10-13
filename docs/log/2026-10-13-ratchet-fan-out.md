# Ratchet counts direct fan-out per module (shipped)

Why: a module that imports many other modules is hard to read in one session and is
where splits go wrong. The assessment (section 2.5) sets a budget of 25 direct imports
of other `coscribe` modules per module; the ratchet now counts it so it can only go down
(issue #112, part of #105).

## Shipped
- `office-agent/scripts/ratchet.py`: new metric `fan_out`. For each module under
  `coscribe`, the number of distinct other `coscribe` modules it imports directly, read
  from grimp's import graph (a package's `__init__` is one module, external packages are
  not counted). Only modules above 25 are listed.
- `office-agent/quality/baseline.json`: `fan_out` section with the two modules over the
  limit today: `coscribe.conversation.session` 41, `coscribe.web.app` 32. The assessment
  measured 43 and 34 earlier; the code has changed since.
- `office-agent/tests/test_ratchet.py`: a module over the limit is listed with its
  distinct imports, a decrease is accepted, an increase fails `--enforce` and `--update`.

## Not verified
- Windows: the metric only reads source files; it was run on Linux.

## Follow-ups
- Reducing any module's fan-out is out of scope here.
