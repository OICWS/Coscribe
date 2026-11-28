# An approval card says which rule asked, and the side panel counts them (shipped)

Why: in Auto mode an office task can raise a run of approval cards, and nothing said which rule
raised each one, so there was no way to tell which rule to change first (#1106, step 1 of the
design agreed with Collins).

## Shipped
- `conversation/approvals.py`: every branch that puts a call to a person names the rule that did
  (`wire.AskReason`): a command without the elevated sandbox, a sandboxed command with network,
  a workspace `ask` rule, Auto mode's reviewer blocking three in a row, the reviewer giving no
  answer, or the approval mode in force. The `approval_required` event carries it as
  `asked_because`; nothing about what is approved changed.
- `runtime_lg/audit.py`: an entry keeps `asked_because` (also for a run nobody watched, where
  the call is refused); `AuditLog.for_thread` reads one conversation's entries and
  `AuditLog.summary` counts the asks by rule against the calls that went ahead without one.
  Lines written before keep loading (`asked_because` is None).
- `GET /api/threads/{id}/activity` returns `approvals`; the side panel's Context shows
  "N asked you · M went ahead without asking" with a chip per rule
  (`frontend/src/components/contextParts.tsx`), and a card adds one line saying why it asks
  when the reviewer's own note doesn't already (`frontend/src/lib/askedBecause.ts`).

## Block 1: fewer reviewer calls and fewer "no answer" cards
- `conversation/approvals.py`: in Auto mode a WRITE_LOCAL call of a file or document tool
  (`write_file`, `edit_file`, the docx/xlsx/pptx edits) goes ahead without the reviewer, as in
  Accept Edits; the audit reason is `auto_mode_edit`. The tools keep those inside the
  conversation's folders. `delete_file` and `move_file` take away a file that was there, so they
  still go to the reviewer, as do tasks, connectors, the browser and commands.
- `runtime_lg/auto_review.py`: a reviewer that fails or gives no verdict is asked once more,
  then the conversation's own model (when a side model is set), before the call reaches a
  person. A weak side model that keeps answering without a verdict was the likely source of the
  run of cards Collins saw.

## Block 2: commands to the reviewer, "allow similar" and Bypass mode (decision 0062)
- `conversation/approvals.py`: in Auto mode a command 0022 kept for the person (no elevated
  sandbox, or network on) goes to the reviewer, which is told where it runs
  (`approval_scope.reviewer_where`); outside Auto mode the person still approves it. The command
  rule moved to `approval_scope.command_rule`.
- A card offers "Allow X in this chat" (`approval_scope.similar_call`): a command line by its
  program, not when chained; any other tool by its name; not the code module. The session keeps
  the allowance; the audit reason is `allowed_similar`.
- Bypass mode (`/bypass`, the mode pill) approves every gated call, audited as `bypass`, only
  while Settings › General's "Allow bypass permissions mode" (`COSCRIBE_ALLOW_BYPASS_MODE`, off
  by default) is on; hooks, exec policy's forbidden rules, the workspace's deny and ask rules, a
  switched-off capability and the sandbox still hold, and a scheduled run keeps its task's tier.
- The mode state moved into `turn_text.PermissionModes`; `runtime_lg` exports `MODE_NOTES` in
  place of the four mode notes.

## Measured
Six office eval tasks in chat Auto mode on `deepseek:deepseek-flash`, with a person who approves
every card (pptx 01 and 07, xlsx 02 and 05, docx 01 and 07; Linux, so no command sandbox;
about $0.10): no card at all. All 55 gated calls went to Auto mode's reviewer and it allowed
54 (it blocked one `delete_file`); no task ran a command line. So the run of cards reported
on a deck did not come from the office tools or scripts here; the card's new line should say
where it comes from on Windows. The reviewer is a model call for each local write in the
workspace (14 to 19 on a deck), which is a cost the next step can cut.

## Not verified
- On Windows with the real sandbox states (not set up, unelevated, elevated with Full network):
  the tests set those states by hand.
- The panel, the card's line and buttons, the mode pill's Bypass entry and the Settings toggle
  were not looked at in a browser here.

## Follow-ups
- Block 3 (workflows): `docs/plan.md`.
- Bypass as the default mode of a new conversation is not offered yet.
