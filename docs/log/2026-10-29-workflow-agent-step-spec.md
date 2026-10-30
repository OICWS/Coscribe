# A workflow can hold an agent step (P1a of #719; partly shipped)

Why: decision 0028 lets a workflow step choose its autonomy. This part puts the agent step in the
spec and on the review card; the engine does not run one yet (P1b).

## Shipped
- `workflow_spec`: `AgentStep` (`kind: "agent"`): `autonomy` `bounded` | `high` | `full`, a
  `goal` with references, `tools` (bounded only, required there), declared `folders` and
  `sites`, output `fields` (none for `full`; with none the result is `{"report": ...}`),
  `max_steps` (default 20, at most 60), `model`, `save_as`. Later steps' references are checked
  against its fields like a model step's. An agent step needs `version: 2`.
- `workflows.permissions`: an agent step's declared folders and sites count in `granted_by`;
  `untrusted_agent_steps` marks the agent steps that read outside content through their
  references (a browser, web or connector tool's result, or anything made from one, a loop's
  item included); `summarize` lists each agent step with its tools, folders, sites, step cap and
  whether it is read-only. `/api/workflows/permissions` passes the browser, web and connector
  tools as the outside ones.
- `workflows.engine`: `preflight` refuses an agent step ("agent steps can't run yet"). The
  helpers that get a model to return a step's fields moved to `workflows/model_step.py`, for the
  agent step to reuse (engine.py 898 -> 830 lines).

## Not verified
- The frontend does not know the new kind yet; nothing creates one (P2 draws it).

## Follow-ups
- P1b: run it through a runner `conversation` injects, the allowlist enforced at `use_tool`,
  the import contract renamed (`docs/plan.md` item 8).
