# The workflows card names its import exceptions (shipped)

Why: a comparison of two fresh sessions (with and without the card) showed the card said
"import from the package" with one exception, while `coordinator.py` and
`tools/scheduled_tasks.py` also import submodules. A session following the card would have
copied them.

## Shipped
- `workflows/AGENTS.md`: names the two other submodule importers and why they stay, and says
  that `UNAVAILABLE_TOOLS` is not what keeps the code module out of a run.

## Not verified
- Whether the card changes how a session handles a real edit; a second comparison with a task
  that edits code is next.

## Follow-ups
- None.
