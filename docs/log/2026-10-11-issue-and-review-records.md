# A change names its issue and links its independent review (shipped)

Why: Step 5 of the structure period (record 0009). The repository had no issues, so claiming work was unused and #64 repeated #63; independent reviews of invariant-path changes left no record on the pull request; and "not verified" items sat in log files that nobody tracked.

## Shipped
- `.github/PULL_REQUEST_TEMPLATE.md` has two new sections: **Issue** (`Closes #N` or `Part of #N`, needed when the change is over about 200 lines, touches a hot file or an invariant path; otherwise `none: <why>`) and **Independent review** (the link to the GitHub review, for invariant paths). The **Not verified** section asks to say whether a script could check the item on Windows.
- `office-agent/CLAUDE.md`: the independent review is run with `/code-review <PR> --comment`, so its findings are posted on the pull request as a GitHub review and the PR body links to it. `AGENTS.md` and `CONTRIBUTING.md` carry the issue rule and the not-verified rule.
- The maintainer's own testing is random use of the app and reporting problems, not a weekly Windows checklist (decided 2026-10-11, record 0009): so no ledger of issues for "not verified" items, and the template and `AGENTS.md` ask only to say plainly what was not tested and whether a script could check it on Windows. What a real Windows machine would catch moves to a Windows job in CI.
- Record 0009 now says the second reviewer from another model family (Codex) waits for the second maintainer; `docs/plan.md` lists it, and "every review thread must be resolved before merge", under Later, both decided on 2026-10-11 to wait.

## Not verified
- That sessions follow the rules; the first pull requests after this show it. Nothing checks them yet.

## Follow-ups
- A Windows job in CI (`windows-latest`) running the platform-sensitive tests: the next step.
- A report-only CI line when a pull request has neither an issue nor `none`, and none of the review link on an invariant path (touches `.github/workflows/`, a `CODEOWNERS` path).
- Labels `task` and `escaped` are all the issue rule needs; the maintainer creates them.
