# 0032: A step says what happens when it fails

Status: proposed (2026-11-02, kurtosisOC; needs the maintainer's acceptance). Narrows 0030 (a
failure no longer always stops the run). Builds on 0028, 0029 and 0030. Issue #776, batch 2.

## Context
Any failed step stopped the run. A rates site that didn't answer for a minute failed a monthly
task, one unreadable invoice of fifty stopped the other forty-nine, and no one heard of a failed
run unless they opened the app.

## Decision
- **A work step (tool, script, model, agent) may set `on_failure`:** up to 5 `retries`,
  `wait_seconds` apart (at most 300), then `stop` the run, `skip` the step, or run `steps` in its
  place, which read `failure.step` and `failure.message`. Each try is its own graph step, so a
  pause or crash during one resumes that try; only the last try is healed (0030).
- **A step marked irreversible (0029) is never tried again on its own**: the spec refuses it.
- **Scope:** a skipped step's result can't be read after it; one replaced by steps can, only when
  those steps make the same name, as after a branch.
- **A loop may skip an item** (`on_item_failure: skip`): a step that still fails inside it leaves
  that item, loops inside the item stop there, and the loop lists each skipped item and why.
  When every item fails, the loop fails.
- **`after_failure` steps run when the run fails**, not when a person said no (work steps only,
  nothing in their place), with the inputs and `failure`. No one may be watching, so they never pause: what would ask is
  refused. Their failure is on their record and never replaces the run's own error. A test run
  leaves out the ones marked irreversible and waits at most 5 seconds between tries.
- **Nothing is counted silently as success.** A recovered failure is a `failed` record with
  `recovered` and `attempts`; the report lists it apart, and a loop's report counts the items
  that worked.
- **What a failure says is outside content**: an agent step reading `failure` gets read-only
  tools (0028).
- A declined approval still stops the run, in a skipping loop too: a person's no is an answer.

## Consequences
- The editor shows the setting on the step's card and in both editors; the run view shows a
  recovered step in amber, never as the step that stopped the run.
- A workflow without these fields runs as before; no new version.
- Out of scope: retrying a whole run, and a different wait per try.

Retired wording: "A failure stops the run, and"
