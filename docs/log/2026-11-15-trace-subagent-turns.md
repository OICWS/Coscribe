# A sub-agent's run and a workflow agent step leave their own line in the turn record (shipped)

Why: the record of how each turn went (decision 0045, #867) counted only a conversation's own
turns. A sub-agent's model calls and tools, and those of a workflow's agent step, went
uncounted, so a turn that delegated most of its work looked cheap and a failing sub-agent tool
never showed up.

## Shipped
- `runtime_lg/agent_stream.py` (new; `stream_turn` and `ModelStalled` moved out of
  `subagents.py`): one streamed pass of a sub-agent or a workflow agent step, which now hands each
  event to a `RunRecord`. `runtime_lg` keeps no record itself: `SubAgentHost` and
  `WorkflowAgentRunner` take a `record_run` that the conversation fills in
  (`conversation/turn_record.py`'s `run_recorder`), so the file stays the conversation's and
  `runtime_lg` exports no new name.
- A sub-agent's run leaves one line in `turns.jsonl`, with the parent conversation's id, `kind`
  `subagent`, its `task_id` and model, ending `completed`, `stopped` or `error` (a stalled model is
  `ModelStalled`).
- Each pass of a workflow agent step leaves one line, `kind` `workflow_agent`, with the workflow
  run's id and the step's key. A step that stops to wait for a person leaves a line for the pass
  that stopped and another for the pass that resumes it; a waiting pass reads `completed`.
- A conversation's own turn now says `kind` `conversation`.
- Decision 0045 says what is counted now.
- Tests: `tests/test_subagent_tasks.py` (a run's line, a stalled run's line),
  `tests/test_workflow_agent_runner.py` (a step's line, a line per pass across a pause).

## Not verified
- A real provider's token numbers for a sub-agent: the tests' models report none.
- The wiring in `conversation/subagents.py` and `workflow_drafting.py` is one argument each and
  has no test of its own through a real conversation.
- Windows.

## Follow-ups
- Side calls (titles, suggestions, the wrap-up a sub-agent writes when out of steps) are not
  counted.
