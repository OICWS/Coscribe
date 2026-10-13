# The approval decision as a table, part 1 (shipped)

Why: `ChatSessionLG._decide_action_request` decides what runs without asking, and
`conversation/session.py` is the next large file to split. A split needs a net that shows the
decision did not change (issue #103, assessment section 4).

## Shipped
- `tests/test_approval_decisions.py`: 35 cases run through the real method with a fake socket.
  Each row names the precedence it protects: stop, hook veto, not gated, plan mode, exec-policy
  rule (forbidden before plan mode, allow after it, ignored for other tools), pre-approved,
  Accept Edits (local writes only), a scheduled run's tier (skip: every risk; auto: local
  writes only), asking a person, refusing when unattended. A row checks the decision, the
  audit record's reason and decision, whether `tool_started` or `approval_required` was sent,
  and that no approval is left pending.
- Mutation check: changing a precedence makes named rows fail, and a decision that asks by
  mistake fails an assertion instead of hanging (the helper answers any question it is asked).
  Ten changes were tried (Accept Edits or Auto approving every risk, the exec-policy `allow` or
  `forbidden` checked on the other side of plan mode, plan mode lifted for a pre-approved tool,
  the hook veto, the stop, the unattended refusal, gated tools approved without asking,
  pre-approval ignored); each failed 1 to 29 rows.

## Not verified
- Auto mode's reviewer, the code module's allowances and the question, plan and task-draft
  tools are part 2.

## Follow-ups
- Part 2 and 3 of #103. `session.py` is not split until the table covers them.
