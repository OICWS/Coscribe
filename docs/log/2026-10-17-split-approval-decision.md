# `approvals.py` decision split by precedence step (shipped)

Why: #348 item 4. `ApprovalDecider._decide_action_request` was 289 lines and complexity 25, the longest function in `conversation/`, and it holds the approval precedence.

## Shipped
- `conversation/approvals.py`: `_decide_action_request` keeps the stop check, the hook veto, the question and draft flows and the ungated approve. The gated part moved to `_decide_gated_request` (exec policy forbids, plan mode, exec policy allows, code allowance, accept-edits and auto mode, then the reviewer and the unattended backstop), with `_auto_review_decision` (the reviewer's verdict and the pause counters) and `_ask_person` (the pending future and the `approval_required` message). `_audit`, `_approved` and `_denied` replace the repeated audit and approve blocks. The order of the checks, every audit record and every returned decision are unchanged.
- `runtime_lg` exports `AuditDecision` and `AuditReason` (the existing audit literals) so the helper is typed without a deep import; its card lists them.
- `quality/baseline.json`: `long_functions` 35 to 34, `complex_functions` 19 to 18.

## Not verified
- `tests/test_approval_decisions.py`, `tests/web/test_chat.py` and `tests/web/test_subagents.py` pass locally; no approval card was clicked in the desktop app.

## Follow-ups
- Left over 300 lines: none. `conversation/session.py` is still 1,472 lines against the 1,300 goal.
