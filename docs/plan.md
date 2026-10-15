# Plan: what is open now

Short on purpose. What shipped lives in [`docs/log/`](log/) (newest) and
[`office-agent/ROADMAP.md`](../office-agent/ROADMAP.md) (short index of the older history); why things
are the way they are lives in [`docs/decisions/`](decisions/) and
[`ARCHITECTURE.md`](../ARCHITECTURE.md). Update this file in the PR that
changes the picture; keep it under about 150 lines.

Last reviewed: 2026-10-15.

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
   Batch 6 (#232), state on 2026-10-15:
   - Done: the Windows job exists (nightly, report only); mutation survivors #221 to #227 and
     #165; the browser-panel port (#209); package cards for every package; guardrails 9
     (security audit and Dependabot, major versions ignored), 10 (dead code ratchet) and 11
     (flaky tests reported, then quarantined with an end date).
   - Done: `conversation/session.py` is split (1,472 lines; hooks, folder and skill changes,
     the turn stream and the approval resume are their own modules).
   - Done: `tools/presentations.py` is a 83-line entry point (parts 1 to 11 of its split; the
     toolkit is `office/pptx/toolkit.py` and the topic mixins, the tool wrappers are
     `office/pptx/tool_wrappers.py`, 88 lines, plus five `wrappers_*.py` topic modules). It was one
     1,464-line function before part 11.
   - Done: `deep_imports` is 37 (exit criterion 40 or fewer; #298).
   - Open: the Windows job must be green 14 days before it is required. It was red on 10-14
     (#267: `os.replace` raised PermissionError in `tools/tasks.py`; fixed 10-15), so the 14-day
     clock runs from the first green nightly after that fix.
   - Open: `test_tool_schema_snapshot` fails in cloud containers but passes in CI (#252).
   - For the maintainer: switch on Dependabot security updates, secret scanning and push
     protection in the repository settings (listed in #263).

0b. **The office route** (decision 0010, `docs/assessments/2026-10-13-office-route.md`):
   new decks compiled from whole-page SVG sources, edits through the page source and upgraded
   object tools; open-source code reused as owned copies. Done: the evaluation and the baseline
   of today's route (`office-agent/evals/`), the engine's compiler (#141), its checks and folder
   build (#198, PR 1), the build tool and an `engine` route in the evaluation (PR 2), the
   measurement (PR 3: the engine wins new decks, design 3.97 against 3.11, at 0.94 times the
   cost), and new decks built from pages in the product (PR 4; a user's template and edits stay on
   today's tools), the PowerPoint instructions cut to what templates and edits need (prompt 22%
   shorter). PowerPoint part 2 so far: native charts and tables, the user's template built from
   pages, Windows font metrics, speaker notes, a design spec from ppt-master's styles, icons,
   SVG illustrations, talk-or-read density, the table and unit-number checks and a repair cap,
   a deck in half the time (#304: no preview loop, no reviewer round; about 6 minutes and 0.4
   yuan a 16-page deck), redesigning a user's deck (task 15: 5 minutes, every picture kept) and
   licensed photos. Edits inside the compiled groups work (tasks 07 and 11, about 2 minutes).
   PowerPoint is done for now; left, each only when a real case asks for it: a check of names
   (people, companies) against the sources, not only numbers; lifting a slide back to SVG
   (ppt-master's 20k-line PPTX-to-SVG code; task 15 showed a redesign does not need it); a
   group's own rotate and scale. Next: Excel, then Word, the same way: their baselines are done
   (#164: Excel PR #181, Word with it; the `current` route on eight tasks each), and the two
   defects they found are fixed (#193 column widths, #219; #197 Word contents list, #216).
   Excel research done (`docs/assessments/2026-10-15-excel-quality.md`): on two new open tasks
   a workbook written whole scored 4.1 on design against 2.8-3.2 for the many-small-tools
   route, at the same cost. Next: a `build_xlsx` tool writing blocks of cells with their
   styles in one call, as Claude for Excel's `set_cell_range` does (part 1 unused, part 2 the
   skill and the measurement), with print-layout, clipped-text and edit-style checks. Its
   engine is openpyxl and LibreOffice first (no Excel needed); real Excel through COM, and an
   Office.js add-in, are later engines behind the same interface, chosen from real use.
   Instructions are changed by cutting first and measuring after: a shorter prompt that scores
   the same is the better one.

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

- A reasoning-effort choice for the user (#202): done (the scale and its mapping per model, the
  pill and slider, the evaluation on the same scale). Left: a look in the dark theme.
- The context panel: show the deferred system and MCP tools as their own rows (not counted in
  the window), and find why system tools read 38.2k at the start of a conversation while the
  bound tools measure about 4.9k tokens (`tests/tool_schemas.txt`).

- Require every review thread to be resolved before a pull request can merge (a ruleset
  setting): not needed at today's size; the maintainer decided on 2026-10-11 to wait.
- A second model family (Codex) reviewing invariant paths: when the second maintainer
  joins (decision 0009).

- Conversations messaging each other (record 0008, accepted and built; see its record).

- Network access per session (an Edit environment setting). Without a sandbox it
  could only switch off coscribe's own web tools; it must say so on its face.
- A callback helper so a script can use a secret (needs its own local
  authentication).
- A terminal UI.
