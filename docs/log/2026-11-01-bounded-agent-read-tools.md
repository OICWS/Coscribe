# A bounded agent step starts with the tools that read files (shipped)

Why: the data eval (#768) found a drafted bounded agent step stopping a run to ask before it
listed or read a file in its own workspace. A bounded step may call only the tools it lists
(decision 0028), and a draft often listed only the tool that does the work. The maintainer chose
to add the reading tools when a step is drafted or added, not to loosen what a run allows.

## Shipped
- `workflows/solidify.py`: `with_read_tools` adds `list_files`, `get_file_info` and `read_file`
  to every bounded agent step of a draft and of a revision, inside loops and branches too, when
  the environment has them. The rule a run applies (`agent_step.decide`) is unchanged.
- `frontend/src/lib/workflowEdit.ts`: a new agent step in the editor lists the same three tools
  (`READ_TOOLS`), and `AgentEditor.tsx` gives them to a step switched back to "Within limits"
  with no tools. The person can still remove any of them.

## Not verified
- On Windows, in the desktop app. Checked with the unit tests and the agent-step e2e spec.

## Follow-ups
- None.
