# Working in this repo

This is `coscribe` (office-agent). Start here, then follow the pointers
below to the doc that actually has the detail you need -- this file is
deliberately short; it's a map, not the content.

## Where the real context lives

- `README.md` -- what coscribe is, setup, feature docs.
- `../ARCHITECTURE.md` -- why the runtime is built the way it is.
- `../docs/plan.md` -- what is open now; `../docs/decisions/` -- why the
  load-bearing decisions were made; `../docs/log/` -- what shipped, one file
  per piece of work.
- `ROADMAP.md` -- a short index of what was built, by phase, plus the old open
  items. The full phase-by-phase history (8.9k lines, frozen 2026-10-08) is
  `../docs/history/roadmap-through-2026-10-08.md`: `grep -n "^## Phase 8ax"`
  it, don't read it whole. Entries there that name `docs/ui-references/*.png`
  refer to reference screenshots deleted once that redesign was built.
- `PPTX_DESIGN.md` -- every PPTX-tool design decision, numbered
  sections, chronological. Read before touching anything in
  `tools/presentations.py`.
- `src/coscribe/runtime_lg/README.md` -- the LLM-runtime migration
  history, real bugs found live, and open research (e.g. the
  tool-loading context-cost investigation and the provider tool-search
  gap).

- `src/coscribe/<package>/AGENTS.md` -- a package's card (purpose, public interface,
  dependencies, invariants, tests). Read it before the package's source, and import from
  the package (`from ..workflows import ...`), not from a submodule, for any name on its
  card. `tests/test_module_cards.py` keeps a card equal to the code. Cards exist for
  every package: `code_runtime`, `conversation`, `runtime`, `runtime_lg`, `tools`,
  `web` and `workflows`. The single modules (`cli`, `config`, `coordinator`, `needs_permission`)
  have none: the test only reads packages.

Every one of these is written the same way: real findings, real
numbers, real bugs -- not guessed. Match that bar in anything you add
to them, and check them before assuming something is undocumented.

## Code review: Open Code Review, delegation mode

Decided explicitly (2026-09-16, to cut token spend on review passes):
before marking a pull request ready, run a self-check pass through
`ocr` (`alibaba/open-code-review`, installed globally via
`npm install -g @alibaba-group/open-code-review` -- reinstall if a
fresh container doesn't have it) in **delegation mode** -- no Claude
Code plugin/marketplace registration needed, no separate LLM/API key
for OCR itself:

```bash
ocr delegate preview --commit <sha>       # or --from/--to for a range
ocr delegate rule <changed-file> [<changed-file> ...]
```

`preview` lists which changed files are actually reviewable (filters
out e.g. markdown). `rule` returns the resolved, precision-tuned rule
set for those files' language, grouped by content -- read it, then
review the real diff yourself against those rules (you are the "host
agent" in OCR's own terms; it does file selection/rule-matching, you do
the judgment). Verified live before adopting: correctly stayed silent
on an already-verified real commit (no false positives), and correctly
flagged a deliberately-planted mutable-default-argument bug in a
synthetic test. Favor precision over recall per the rule set's own
instruction -- only raise something you're actually confident about.

This is the author's self-check, and it is the same model reviewing its own
work. A pull request that touches an invariant path also needs an independent
review by a session that did not write it: one the maintainer starts
(`/code-review <PR number> --comment`, or a prompt naming the PR), or a
collaborator's. Either way the findings are posted on the pull request as a
GitHub review, and the PR body links to it: the PR page then shows that the
review happened and what it found, which a conversation does not.
Invariant paths: `runtime/secrets*.py`, `runtime/secret_store.py`,
`runtime_lg/tool_deferral.py`, `runtime_lg/mcp_oauth.py`,
`code_runtime/permissions.py`, `coordinator.py` (the instructions and the core
tool names), and anything that opens a network listener.

## Code comments: WHY only, never WHAT or history

A comment earns its place by explaining a non-obvious design reason --
a hidden constraint, an invariant, a workaround, something that would
surprise a reader. Real drift caught and corrected 2026-09-18: comments
kept accumulating three other kinds that don't belong in code at all --

- **Restating WHAT the code does** ("renders X as Y ⟨chip⟩") -- the
  code already says this; delete.
- **History/evolution narration** ("this used to X", "a user reported
  Y, this closes that gap", "real gap this closes: ...") -- this is a
  commit-message sentence wearing a `#`. Put it in the commit message
  (or PR description) instead, never in the code.
- **Product/UX reasoning or restated user intent** ("用户想要...于是
  ...", "a manual button read as unnecessary friction so...") -- same
  answer, same destination: commit message, not a comment.

Before writing a comment, ask whether it survives with every sentence
that isn't a "why" removed, and whether a reader with zero memory of
this conversation still needs it. If not, it goes in the commit
message or gets deleted outright -- never both.

## Commit authorship

Commits are authored as the human whose session it is, not as Claude (decided
2026-09-26, per person since 0007). A fresh container starts with git's identity
set to Claude, so set it in the clone before the first commit, to that person's
own GitHub name and their GitHub noreply address
(`<id>+<login>@users.noreply.github.com`; the id is on the person's GitHub
profile API, `https://api.github.com/users/<login>`). Never copy another
person's identity, and never use an address the person no longer uses.

Write no `Co-authored-by` or `Co-Authored-By` trailer: a squash merge copies
every commit author and trailer into the merged commit. The maintainer's, as an
example of the form:

```bash
git config user.name "OICWS"
git config user.email "216505477+OICWS@users.noreply.github.com"
```

## Delegating simple code changes

Simple, well-specified edits (remove an entry, rename, adjust a test,
drop an icon) go to a Sonnet subagent (`Agent` with `model: "sonnet"`)
to save tokens -- give it the exact files, the change, the repo's comment
rule, and the lint/test commands to run. The main session keeps the core
thinking and design, complex or high-risk backend code, all frontend
code, prompt/instruction wording, and live verification -- and reviews
the subagent's diff before committing.

## Repository -- how a change reaches `main`

All development happens in `OICWS/coscribe`. The private `OICWS/project` repo
was the development repo until 2026-09-30, when the two held identical trees;
it is frozen now and is neither pushed to nor read.

`main` is protected: **every change, the maintainer's and doc-only ones too,
goes through a pull request** whose `test` check is green, squash-merged.
Nothing is pushed to `main` directly.

- Branch name `<area>/<slug>` (areas: runtime, tools, server, workflows, code,
  secrets, frontend, desktop, docs).
- Open a *draft* PR with your first push, titled `[area] goal`, with a
  "Touches:" line naming the hot files you expect to edit. The list of open PRs
  is the board of who is doing what.
- Before editing a hot file (`web/app.py`, `conversation/session.py`,
  `coordinator.py`, `frontend/src/App.tsx`,
  `frontend/src/types/*.ts`), look at the open PRs; if someone is changing the
  same part, tell the maintainer instead of racing.
- One area per PR, about 600 changed lines at most (generated catalogs and
  icons excepted). Land partial work behind an unused code path ("part 1:
  nothing applies it yet") instead of stacking PRs.
- No signature lines: a commit message, PR title or description has no
  `Co-authored-by`, session link or "Generated with/by ..." line. The `PR text`
  check fails a pull request that has one.
- Update an open PR with `git merge origin/main`, not rebase and force-push.
- **Never merge a PR, enable auto-merge or push to `main`.** The maintainer
  merges, when the PR's checks and `main`'s latest run are green.
- **`main` is red:** nothing merges except the fix. If the cause is the last
  merged PR and no fix PR is open within 15 minutes, open a `git revert` PR.

`git fetch` through this environment's proxy can return a stale
cached read -- if the branch state looks wrong, cross-check with
`git ls-remote origin main` (a live query) before trusting `fetch`.

## Test discipline

Tests of the web server live in `tests/web/test_<domain>.py` (chat, threads,
connectors, settings, skills, scheduled, subagents, internal; chat and threads are split
into `test_chat_<topic>.py` and `test_thread_<topic>.py`); a new test goes into
the file of its domain, and fakes and builders shared by several files go into
`tests/web/helpers.py`. Do not start a new catch-all file.

A new WebSocket event is added to `conversation/wire.py` first; every payload a test sends is
checked against it.

A test that fails and then passes on the one rerun CI allows (`--reruns 1`) is a flake, not a
pass: the run lists it at the end and in the job summary. Open an issue for it and mark it
`@pytest.mark.quarantine(issue=N, until="YYYY-MM-DD")`, at most a week out. It keeps running and
may fail meanwhile; after the date it fails with the issue's number (`tests/flaky_policy.py`).
Do not assert on elapsed wall-clock time.

CI is the gate. Before pushing run `bash scripts/check.sh --fast` (frontend
build, oxlint, ruff, mypy) and the test files for what you touched; before
marking a PR ready, wait for a green CI run (or run the full
`bash scripts/check.sh`, about 4 minutes on 4 CPUs). A test that
writes real files must `monkeypatch.chdir(tmp_path)` first if it (or
code it calls) can fall back to a relative path -- a real, live-hit
mistake this session made once already (see `test_web.py`'s own
`test_post_provider_persists_an_absolute_path_not_a_cwd_relative_one`
for the established pattern to copy).

## Cloud sessions: environment and live testing

In a git worktree the `.venv` is the main checkout's and imports its `src`, and `web/static/` (the
built UI) is missing: run `PYTHONPATH=src` with that venv's python, and create an empty
`src/coscribe/web/static/` for tests that build the app (remove it afterwards).

`.claude/hooks/session-start.sh` installs everything (venv, frontend
`node_modules`, `ocr`, LibreOffice, poppler). In this container
`NO_PROXY` sends pypi/npm direct and apt's sources are `http://` -- both
get 403; the hook routes them through `HTTPS_PROXY`. A command you run
yourself that installs packages needs the same: export
`NO_PROXY=localhost,127.0.0.1` (and `npm_config_noproxy` to match) first.

Model keys come from the environment settings and reach only sessions
started after they were added -- never ask for one in chat. With
`DEEPSEEK_API_KEY` set, register it as a custom provider
(`COSCRIBE_PROVIDERS_CONFIG_PATH`, base_url `https://api.deepseek.com/v1`)
and confirm the model id from `GET https://api.deepseek.com/models`
before using it. Without a key, `scripts/stub_llm.py` is a local
OpenAI-compatible model that always answers "OK": enough for UI e2e
(e.g. `sidebar.spec.ts`), not for specs that check what the model says
(`chat.spec.ts` looks for "4").

Live runs: `coscribe-web` (port 8000) started from a scratch directory
holding its own `.env` and workspace, `npx vite --host 127.0.0.1` in
`frontend/` (port 5173), then `npx playwright test <spec>`. Start both with the same
`COSCRIBE_LAUNCH_TOKEN=<anything>`: the Vite page has no token of its own, so Vite adds it to
what it proxies.

Which model a test run of ours uses: DeepSeek with `reasoning_effort: "low"`
by default (measured 2026-10-13 on generated decks: judged level with the
default `high` and up to 35% cheaper; `none` broke pages; most of the cost
is the model's reasoning output, not cache misses:
`docs/assessments/2026-10-13-office-route.md`). The Gemini key is free tier:
20 requests a day per model and no Pro quota, enough for small checks only.

Long live runs on DeepSeek (multi-turn tasks, benchmarks, anything over a
few calls) go off-peak: weekdays 9:00-12:00 and 14:00-18:00 Beijing time
cost double (checked on DeepSeek's pricing page 2026-10-05; re-check
before relying on it). Outside those hours, start now; inside, schedule
the run (`send_later`) rather than paying peak. This is for our own
testing only -- the product doesn't time anything around one vendor's
prices.

## Model-name / provider facts: verify, don't guess

This session repeatedly found stale/wrong model names and provider
capability assumptions from training-data priors (e.g. a hardcoded
`"claude-opus-4-6"`, an assumed-wrong DeepSeek model id). Anything
about a specific model name, a vendor's current API capability, or
"is this library still maintained" gets checked live (WebSearch/
WebFetch against the vendor's own docs) before it goes in code, a
default value, or documentation -- not answered from memory.
