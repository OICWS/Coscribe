# A change names its issue and links its independent review (shipped)

Why: Step 5 of the structure period (record 0009). The repository had no issues, so claiming work was unused and #64 repeated #63; independent reviews of invariant-path changes left no record on the pull request; and "not verified" items sat in log files that nobody tracked.

## Shipped
- `.github/PULL_REQUEST_TEMPLATE.md` has two new sections: **Issue** (`Closes #N` or `Part of #N`, needed when the change is over about 200 lines, touches a hot file or an invariant path; otherwise `none: <why>`) and **Independent review** (the link to the GitHub review, for invariant paths). The **Not verified** section asks for an issue number after each item that needs a real machine or an account.
- `office-agent/CLAUDE.md`: the independent review is run with `/code-review <PR> --comment`, so its findings are posted on the pull request as a GitHub review and the PR body links to it. `AGENTS.md` and `CONTRIBUTING.md` carry the issue rule and the not-verified rule.
- Record 0009 now says the second reviewer from another model family (Codex) waits for the second maintainer; `docs/plan.md` lists it, and "every review thread must be resolved before merge", under Later, both decided on 2026-10-11 to wait.

## Not verified
- That sessions follow the rules; the first pull requests after this show it. Nothing checks them yet.

## Follow-ups
- The not-verified ledger: one issue per item that still needs a real machine or an account, labelled `needs-real-machine` or `needs-account`, from `docs/plan.md` and the recent logs.
- A report-only CI line when a pull request has neither an issue nor `none`, and none of the review link on an invariant path (touches `.github/workflows/`, a `CODEOWNERS` path).
- Labels `task`, `needs-real-machine`, `needs-account`, `escaped`, `freeze`, `review:independent-done` are created by the maintainer.
