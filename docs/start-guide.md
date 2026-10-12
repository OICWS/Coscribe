# Start here: from invite to first pull request

For a new person and their own Claude Code or Codex session. The rules live in
[`CONTRIBUTING.md`](../CONTRIBUTING.md), [`AGENTS.md`](../AGENTS.md) and
[`office-agent/CLAUDE.md`](../office-agent/CLAUDE.md); this page only gives the order.

1. **Accept the invite.** You join `OICWS/coscribe` as a collaborator, not a fork, so CI and
   the ruleset apply to you as to everyone.
2. **Clone, then set your identity before the first commit.** A fresh clone or cloud
   container may carry another identity (Claude's), and commits would be authored as it:
   ```bash
   git config user.name "<your GitHub login>"
   git config user.email "<id>+<login>@users.noreply.github.com"   # id: https://api.github.com/users/<login>
   ```
   Never copy someone else's identity. A commit, PR title or PR description has no
   `Co-authored-by`, session link or "Generated with" line; the `PR text` check fails the PR.
3. **Set up** as in [`README.md`](../README.md) (a venv in `office-agent/.venv`, `npm install`
   in `office-agent/frontend`). Then run `cd office-agent && bash scripts/check.sh --fast`;
   it must pass before you change anything. `scripts/check.sh` finds `.venv` itself, but
   `pytest` on its own needs the venv active (or call `.venv/bin/python -m pytest`).
   The fast check needs no model key.
4. **Read, in this order:** `AGENTS.md`, all of `office-agent/CLAUDE.md`, `docs/plan.md`,
   and [`docs/decisions/README.md`](decisions/README.md). Read a decision record before touching
   anything an invariant in `AGENTS.md` covers, and
   [`0007`](decisions/0007-working-with-more-than-one-human.md) for how people and sessions
   share the work.
5. **Pick a `task` issue and claim it with a comment** (area, hot files) before you start.
   The open issues and PRs are the board; a new task uses
   [`.github/ISSUE_TEMPLATE/session_task.md`](../.github/ISSUE_TEMPLATE/session_task.md).
   Start with a docs or tests task; skip invariant paths (they need an independent review).
6. **Branch `<area>/<slug>`** (areas: runtime, tools, server, workflows, code, secrets,
   frontend, desktop, docs), from a fresh `origin/main`. If `git fetch` looks stale behind a
   proxy, cross-check with `git ls-remote origin main`.
7. **Make the change, small and in one area,** with its test. Add
   `docs/log/<date>-<slug>.md` in the same PR (format: [`docs/log/README.md`](log/README.md))
   and update `docs/plan.md` if the open work changed.
8. **Push and open a draft PR** titled `[area] goal`, filling
   [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md): the issue
   (`Closes #N`), a "Touches:" line, and a plain "Not verified" section.
9. **Keep it current** with `git merge origin/main`; never rebase or force-push an open PR.
   Fix a red `test` check before asking for review.

## What the maintainer does

The maintainer reviews and squash-merges when the checks are green. Sessions never merge,
enable auto-merge or push to `main`. A change to an invariant path also needs a review by a
separate session, posted on the PR with `/code-review <PR> --comment`.

## A red ratchet

`bash scripts/check.sh` compares numbers about the code (file length, deep imports, ...) with
`office-agent/quality/baseline.json`. If one got worse, fix the code. Never run
`scripts/ratchet.py --update --accept-worse` and never edit the baseline upward: only the
maintainer does.
