# The instructions say how scripts really run, and ask no set questions (shipped)

Why: the audit of 2026-11-10 found that the coordinator's instructions told the model scripts run
"with no sandbox at all", which decision 0021 makes untrue where the self-test passed, and that
they made the model stop for an answer before its first sub-agent and before drafting a workflow.

## Shipped
- `coordinator.py`: a script is held to the conversation's folders where isolation is on, and runs
  as the user only where it is off and the person allowed scripts anyway.
- A sub-agent runs on the conversation's model unless the person names another configured model;
  the model no longer asks with a "Sub-agent model" question.
- The model picks a workflow's kind itself (fixed steps for work done here with tools that should
  repeat the same way, written instructions otherwise) and says in one sentence which it chose,
  instead of a "Workflow type" question.
- `tests/test_coordinator.py` checks the three; `tests/tool_schemas.txt` regenerated.

## Not verified
- A live conversation on Windows that delegates and drafts a workflow with the new wording.
