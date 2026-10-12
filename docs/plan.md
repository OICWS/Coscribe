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
      the Windows run is red when a test fails. Changed-line coverage stays report-only until
      we know how many recent pull requests would have failed 80%.
   Then golden-file and approval tests, and only after them the large splits (roadmap in
   the assessment).

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
2. **Working with more than one person** (record 0007, accepted): when the second
   maintainer joins, an admin adds them as collaborator, their handle goes into
   `.github/CODEOWNERS`, and the ruleset requires code-owner review for those paths.

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
