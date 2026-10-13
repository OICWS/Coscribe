# Split ChatSessionLG, part 1: the approval decision moves to conversation/approvals.py (shipped)

Why: `ChatSessionLG` is 3,741 lines with about 90 methods, and the approval decision (what runs
without asking) is the security-relevant part and the hardest to review inside it (issue #140,
assessment section 2.2). This is a move; no behaviour changes.

## Shipped
- `conversation/approvals.py`: `ApprovalDecider` holds `_decide_action_request` and the
  question, plan and task-draft flows, `_auto_approves`, `_auto_review`, `_auto_review_active`,
  `_auto_approval_active`, `_effective_run_approval_mode` and `_code_allows`, plus
  `_can_resolve_approvals`. What it needs from the session is the `ApprovalHost` protocol (the
  attributes and methods the moved code touches); the session keeps the pending-approval futures
  and their resolution, the socket, the hooks and the preview.
- `ChatSessionLG` keeps one-line methods of the same names that delegate, so callers and tests
  are unchanged. The moved bodies differ from the old ones only by `self.` -> `self._host.` for
  the session's own state, a re-wrapped line, and one new seam: `_load_exec_policy` on the
  session, which the decision and `_decidable_unattended` both call (a test spies on the
  session module's `load_exec_policy`).
- `session.py` 3,741 -> 3,283 lines; `_decide_action_request` (289 lines, complexity 25) and its
  baseline entries now sit on `approvals.py`; `fan_out` of `conversation.session` 41 -> 40.
- `tools`, `runtime_lg` and `code_runtime` export the names the new module imports, so it
  imports from packages, not submodules, and adds no `deep_imports` entry.
- No test file changed; `tests/tool_schemas.txt` unchanged; `lint-imports` passes.
- Mutation check: moving the plan-mode check after the standing approvals makes 6 rows of
  `tests/test_approval_decisions.py` fail (`exec_allow_does_not_lift_plan_mode`,
  `plan_beats_a_run_that_skips_approval`, `plan_beats_accept_edits`, `plan_beats_preapproved`,
  `plan_mode_beats_a_task_allowance`, `plan_mode_beats_the_setting`).

## Not verified
- The app was not run on Windows; the approval table and the web tests cover the decision.

## Follow-ups
- Splitting `_decide_action_request` itself into smaller methods, and the other parts of the
  session (history, inbox, workflow drafting), are later PRs.
