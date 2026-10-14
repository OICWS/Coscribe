# Plan: what is open now

Short on purpose. What shipped lives in [`docs/log/`](log/) (newest) and
[`office-agent/ROADMAP.md`](../office-agent/ROADMAP.md) (short index of the older history); why things
are the way they are lives in [`docs/decisions/`](decisions/) and
[`ARCHITECTURE.md`](../ARCHITECTURE.md). Update this file in the PR that
changes the picture; keep it under about 150 lines.

Last reviewed: 2026-10-11.

## Next, in order

0. **Structure period** (record 0009; features paused 2 to 3 weeks from 2026-10-11).
   Steps, each one PR or less, from `docs/assessments/2026-10-11-scale-to-1m-lines.md`:
   1. Done: a report-only ratchet and the encoding lint rule; next, `--enforce` after a week.
   2. Done: coverage measured in CI and the two 60-second tests fixed; pytest in parallel
      waits until the tests are shown independent. The coverage floor is 88 (CI: 88.58).
   3. Done: the stale references fixed and `tests/test_doc_references.py` keeps them fixed.
   4. Done: a snapshot of the tool schemas and the system prompt (`tests/tool_schemas.txt`).
   5. Reviews and "not verified" items recorded where they can be found: the PR template
      and the rules ask for an issue and a linked GitHub review (done). A ledger of issues
      for the not-verified items was dropped: the maintainer tests by using the app, and
      what a script can check on Windows goes into a Windows job in CI (step 13 of the
      assessment, brought forward: the next step after this one).
   6. A Windows job in CI (`.github/workflows/windows.yml`): nightly, report only; fix or
      fence what it shows, then make it required after two green weeks.
   7. Public interfaces and cards, one package per PR: `workflows` is the pilot (its card,
      its `__init__.py` as the interface, `tests/test_module_cards.py`); the next package
      follows if the pilot reads well.
   8. The ratchet hardened after the second review: `--update` only tightens (`--accept-worse`
      is the maintainer's), `check.sh` enforces it, `pyproject.toml` is a CODEOWNERS path and
      the Windows run is red when a test fails. Changed-line coverage stays report-only. Measured
      (issue #94, `docs/assessments/2026-10-13-diff-coverage.md`): of the last 20 PRs that changed
      `src/`, 17 measurable, 2 would fail at 80% (one test each), 6 at 90% (pure moves and a
      Windows-only branch). The maintainer decides whether to enforce.
   9. Golden-file tests (assessment step 9). Part 1 (issue #86): the pptx XML is stable once
      canonicalised; 5 decks have goldens (`office-agent/tests/test_office_golden.py`). Part 2
      (issue #89): 18 decks so far, images, charts, icons, shapes and every layout directive added (issue #93: the canonicaliser opens
      the workbook embedded with a chart and blanks its build time); the master, layouts and theme
      are kept once in a shared golden. Next: templates and SmartArt edits, then audio and CJK
      text; then docx and xlsx the same way.
   10. Approval decision table (issue #103): part 1, the precedence of the standing approvals,
       plan mode, the exec policy and asking, is in `tests/test_approval_decisions.py`. Next:
       Auto mode's reviewer, the code module's allowances, the question and draft tools.
   Then the large splits (roadmap in the assessment); the split of `tools/presentations.py`
   waits for the first version of the deck engine below, so it is split once.

0b. **The office route** (decision 0010, `docs/assessments/2026-10-13-office-route.md`):
   new decks compiled from whole-page SVG sources, edits through the page source and upgraded
   object tools; open-source code reused as owned copies. Done: the evaluation and the baseline
   of today's route (`office-agent/evals/`), the engine's compiler (#141), its checks and folder
   build (#198, PR 1), the build tool and an `engine` route in the evaluation (PR 2). Next (#198):
   the measurement against the baseline, cost per deck included (one task cost 1.7 times today's
   route), and only if it wins the switch of new decks to the engine;
   Excel, then Word, the same way.

1. **Make the repository easy to join** (governance review, 2026-10-08).
   - Done: `main` protected by a ruleset (PR only, squash, `test` required),
     `scripts/check.sh` shared by CI and local, root `CLAUDE.md` and
     `AGENTS.md`, templates.
   - Done: `ROADMAP.md` compacted (old one archived in `docs/history/`), plan,
     decisions and log in place, package dependencies checked in CI.
   - Done: `conversation/session.py` and its helpers moved to `conversation/` (the CLI uses
     it; it no longer imports `cli` or FastAPI).
   - Done: the setup page, request models and provider catalog are out of `web/app.py`;
     every HTTP route is in `web/routes/` (one `router(state)` each).
   - Done: the two WebSocket routes are in `web/routes/ws.py`.
   - Done: the server tests are in `tests/web/`, one file per domain.
2. **Working with more than one person** (record 0007, accepted): kurtosisOC is a
   collaborator and an owner on every `.github/CODEOWNERS` line. Left: an admin turns on
   "require code owner review" in the repository ruleset (a settings change, not a PR).

## Needs the maintainer's testing (could not be verified here)

- Sign-in of the 13 connectors added for the skill plugins (only the
  registration was tested), and of the 19 added before them.
- The guided setup for HubSpot and Google (Gmail, Calendar, Drive): follows the
  vendors' guides, tested only against a local OAuth server. Google's Workspace
  MCP servers are a Developer Preview; whether HubSpot accepts a `localhost`
  redirect is not documented.
- Secrets against a real Windows Credential Manager, and a real remote connector
  with a header from Settings > Secrets.
- The attachment cards and the new question-card colours in the desktop app; the
  thin scrollbar on pages in the built-in browser.
- The code module on real Windows.

## Open problems, not reproduced or not solved

- Notion showed no tools for the maintainer; cause not found.
- The built-in browser panel opened during a connector's first connection
  (sign-in pages should open in the system browser); not reproduced.
- A Hugging Face connector call once hung a turn; a 120 s limit and an automatic
  reconnect were added, the cause is unknown.
- Slack is not offered: its MCP is said to be limited to Marketplace or internal
  apps (third-party source, not checked against Slack's docs).
- A sent message does not keep its attached files as cards; the file picker takes
  one file at a time.

## Later (wanted, not scheduled)

- A reasoning-effort choice for the user (#202): part 1, the scale and its mapping per model, is
  in (`runtime_lg/effort.py`); next the pill and slider next to the model, then the evaluation
  through the same mapping.

- Require every review thread to be resolved before a pull request can merge (a ruleset
  setting): not needed at today's size; the maintainer decided on 2026-10-11 to wait.
- A second model family (Codex) reviewing invariant paths: when the second maintainer
  joins (decision 0009).

- Conversations messaging each other (record 0008, accepted and built; see its record).

- Network access per session (an Edit environment setting). Without a sandbox it
  could only switch off coscribe's own web tools; it must say so on its face.
- A callback helper so a script can use a secret (needs its own local
  authentication).
- Splitting `tools/presentations.py` (7k lines) and `ChatSessionLG`, when
  presentation work resumes.
- A terminal UI.
