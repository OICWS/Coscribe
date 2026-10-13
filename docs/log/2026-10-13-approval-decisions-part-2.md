# The approval decision as a table, part 2 (shipped)

Why: part 1 of `ChatSessionLG._decide_action_request` left Auto mode's reviewer, the code
module's allowances and the question, plan and task-draft tools untested. The method is not
split until the table covers them (issue #103).

## Shipped
- `tests/test_approval_decisions.py`: 65 more cases, same fake socket and same checks (the
  decision, the audit records, what the client is sent, nothing left pending).
  - `AUTO_ROWS` (23): the reviewer allows, blocks or gives no answer; the third block in a row
    or the twentieth in all pauses Auto mode and asks a person with a note; an allow ends the
    run of blocks but not the total; approving while paused resumes Auto mode; the reviewer
    comes after pre-approval, Accept Edits, plan mode, exec-policy rules, a hook veto and a
    scheduled run's own tier; unattended, the reviewer still answers and a refusal is last.
  - `CODE_ROWS` (18): a card the person allowed for one task and tool, the Settings > Code
    "allow", and where each one stops (another task or tool, the conversation itself, an
    unattended turn, a scheduled run, plan mode, a hook veto).
  - `QUESTION_ROWS` (24): `ask_user_question`, `exit_plan_mode`, `create_scheduled_task` and
    `edit_scheduled_task` answer "respond" for a stop, a hook veto and an unattended run, and
    for each answer the person can give; plan mode and exec rules do not block them.
- The shared helper `_decide` now answers questions as well as approval cards.

## Mutation check
Fifteen changes to `session.py` were tried, each reverted; each failed 1 to 10 named rows:
reviewer used while paused, three blocks in a row made four, twenty in all made twenty-one,
total not restarted at twenty, an allow not ending the run of blocks, approval not resuming
Auto mode, a silent reviewer approving, the code allowance ignoring the task, the Code setting
reaching a scheduled run or an unattended turn, a refusal using "reject" for question tools, `exit_plan_mode`
outside plan mode asking, approving a plan not leaving plan mode, an unattended question
asking anyway, and question tools gated by plan mode.

## Not verified
- The approval cards' preview and the audit record's contents are part 3.
