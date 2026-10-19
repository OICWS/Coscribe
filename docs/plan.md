# Plan: what is open now

Short on purpose. What shipped lives in [`docs/log/`](log/) (newest) and
[`office-agent/ROADMAP.md`](../office-agent/ROADMAP.md) (short index of the older history); why things
are the way they are lives in [`docs/decisions/`](decisions/) and
[`ARCHITECTURE.md`](../ARCHITECTURE.md). Update this file in the PR that
changes the picture; keep it under about 150 lines.

Last reviewed: 2026-10-15.

## Next, in order

0. **Structure period: done** (record 0009; features paused from 2026-10-11, only the maintainer lifts it; closing report `docs/metrics/2026-10-19-structure-period-close.md`; what stays open is listed there).
   Steps, each one PR or less, from `docs/assessments/2026-10-11-scale-to-1m-lines.md`:
   1. Done: the ratchet and the encoding lint rule; `check.sh` and CI enforce the ratchet (a worse number fails; `tests/test_ratchet.py` keeps that wired).
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
      text. Part 3 (issue #402 item 7): docx has 16 goldens (structure edits and comment
      threads added), xlsx 11 workbooks (`tests/test_xlsx_golden.py`, `tests/xlsx_canonical.py`);
      more tools (pdf, `recalc_xlsx`) the same way.
   10. Approval decision table (issue #103): done in `tests/test_approval_decisions.py` (the
       precedence of the standing approvals, plan mode, the exec policy and asking; Auto mode's
       pause rules; the code module's allowances, including a damaged Settings > Code file; the
       question and draft tools) and `tests/test_approval_records.py` (cards and audit records).
       The reviewer's own side (what it is shown, each odd reply or error) is in the same table
       file.
   Batch 6 (#232), state on 2026-10-15:
   - Done: the Windows job exists (nightly, report only); mutation survivors #221 to #227 and
     #165; the browser-panel port (#209); package cards for every package; guardrails 9
     (security audit and Dependabot, major versions ignored), 10 (dead code ratchet) and 11
     (flaky tests reported, then quarantined with an end date).
   - Done: `conversation/session.py` is split (1,472 lines; hooks, folder and skill changes,
     the turn stream and the approval resume are their own modules).
   - Done: aisuite is no longer a dependency (#299): one `pip install` resolves, the hand-run
     google-genai step is gone from CI and the session hook. Gemini 3.x has effort levels
     again on langchain-google-genai 4.3 (`<4.4` until the google-genai pin can move, #402).
     Gemini 2.x levels via `thinking_budget` are not built: Google no longer serves 2.x to new keys
     (see `docs/log/2026-10-18-gemini-2x-and-libreoffice-inventory.md`).
   - Done: `tools/presentations.py` is a 83-line entry point (parts 1 to 11 of its split; the
     toolkit is `office/pptx/toolkit.py` and the topic mixins, the tool wrappers are
     `office/pptx/tool_wrappers.py`, 88 lines, plus five `wrappers_*.py` topic modules). It was one
     1,464-line function before part 11.
   - Done: `deep_imports` is 37 (exit criterion 40 or fewer; #298).
   - Open: the Windows job must be green 14 days before it is required. It was red on 10-14
     (#267: `os.replace` raised PermissionError in `tools/bookkeeping/tasks.py`; fixed 10-15). The first green
     nightly after the fix was run 23 on 10-15 (main at 8a08b0d), but 10-16 (5 tests, #339, fixed in #340)
     and 10-17 (5 tests, three of them in tests other sessions added that day; fixed in the PR that
     links it) and 10-18 (one test that bounded wall-clock time, 0.84 s against 0.4 s on the runner;
     fixed to wait on events) were red, so the clock starts again from the next green night. A red
     night restarts it.
   - Done: `test_tool_schema_snapshot` is skipped on Python 3.13 (cloud containers), where docstring
     indentation changes every tool description; CI runs 3.11 and is the check (#252).
   - For the maintainer: switch on Dependabot security updates, secret scanning and push
     protection in the repository settings (listed in #263).

0a. **Structure phase 2: components** (#348, decision 0009): the component the unit a session works
   in (card, `__init__.py` interface, tests by path; slice <= 15 files, 150k tokens). Done: the
   component map and generated `CODEOWNERS` (#349); `tools` cut into `tools.office.{docx,xlsx,pdf,pptx}`
   (#350), `tools.exec` (#351), `tools.web` (#352) and `tools.bookkeeping` (item 1); a generated
   `protected` contract per package and a `layers` contract for the office formats, with 3 imports
   (3 of 42 lines) left to shrink (item 2, 6b: the pptx engine); `scripts/slice.py`
   and the discovery protocol in `AGENTS.md` (item 3,
   the measured sample changes are still open). Also done: long functions and fan-out split
   (item 4), `web/tests` split by path (item 5), frontend ratchet and knip guardrails (item 6),
   `docs/security/review-pack.md` (item 7), `scripts/review_pack.py` and
   `scripts/weekly_metrics.py` (item 8). Done: the fresh-session measurement
   (`docs/metrics/2026-10-17-fresh-session-slice.md`, all inside budget; open: a frontend card).
   Open: reading the first `audit.yml` run and the CodeQL alerts after 2026-10-19 (item 7). The next stage is Batch 8 (#388): Origin/Host validation (#390), the first audit and
   CodeQL read, the 281 "Not verified" items sorted (`docs/metrics/2026-10-17-not-verified-triage.md`:
   20 checks for a person), the fresh-session measurement, prompt-injection tests, small items.

   Batch 10 (#425, the last structure batch): item 1 done (a workbook with a cell note now gets its
   formula values), item 3 done (the ratchet was already enforced; now a test keeps it wired), item 4 done (the workflow spec lives in `workflow_spec`, below `tools`; the layers contract ignores nothing). item 5 closed with a reason and item 6 done (the inventory found no product call). Items 8 to 10 (Slides tests, added 10-18): item 8 done (a Playwright spec for the Slides panel, nightly in `e2e.yml`), item 9 done (a property test for arranging and undo), item 10 done (the editor's source functions tested in jsdom, judged by the server's parser). Item 2 done except the CodeQL alerts, which the maintainer reads; item 7 done (the closing report).
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
   skill and the measurement), with print-layout, clipped-text and edit-style checks. Parts 1a, 1b and
   1c are done (1c: the ten single-purpose writers removed, tasks 11 and 12 added; 1d,
   showing a workbook inside the app, was tried and dropped: the user opens it in Excel): the model writes workbooks with write_xlsx_cells and modify_xlsx (design 4.18 on
   the open tasks against 2.88, at the same cost and two thirds of the time). Its engine is openpyxl, with IronCalc for formula values (no Excel needed); real Excel through
   COM, and an Office.js add-in, are later engines behind the same interface, chosen from real use.
   **No LibreOffice in the product** (decision 0012, #319): step 1 (no Office needed) is IronCalc
   for formula values and resvg for a built deck's page previews, PDF pages with PDFium; step 2
   (done; `scripts/check_office.py` passed every case with Microsoft Office on Windows, WPS
   not yet checked), conversion and the exact previews of Word, Excel and PowerPoint files
   through Office (COM), or WPS;
   step 3 (done), the LibreOffice code paths removed, LibreOffice kept for development and the
   evaluation.
   Word research done (`docs/assessments/2026-10-16-word-quality.md`): a document written whole by
   a script scored 4.2-4.3 on design against 3.7-3.9 for `write_docx`, with content level; the gap
   is layout `write_docx` cannot set (a shaded table header, an East Asian font, heading styles,
   page numbers), and the script route added facts and costs more. A new document without a
   template gets a house style compiled onto real Word styles (#325, decision 0013): design 4.0-4.2
   against 3.7 in the same judging, content no lower, cheaper; the gate's 4.2 design was missed by
   0.1 and the maintainer accepted it. Open: the open tasks' layout (09, 10).
   Restructuring a user's document (insert a section, a list, a table or a contents list; move or
   delete a section) is one `edit_docx_structure` call (#329): on task 07 about half the time and
   cost of the scripts it replaced. With `read_docx(view="structure")` (#331) the model checks a
   document without a script too: no script on tasks 07 and 11, 18-47 s a task.
   Instructions are changed by cutting first and measuring after: a shorter prompt that scores
   the same is the better one.
   Viewing the files a run produced, inside the app (Word review with its comments, slides,
   sheets): designs reviewed by the maintainer 2026-10-16. First the window's panels: the panel
   switches moved into the title bar (done), several panels open at once, arranged by
   dragging (#334, done), then the viewers as panels (decision 0014,
   `docs/assessments/2026-10-17-file-viewers.md`): the Word review tools and routes (done, #343),
   the Word panel (read-only, merged #346). Any panel can open in a window of its own (desktop).
   Direction changed 2026-10-17: what coscribe makes becomes an artifact (Slides first, then
   Docs, Design/Dashboard, Sheets last), edited in the app and exported to the Office format; the
   Slides design is settled (decision 0015, `docs/assessments/2026-10-17-slides-artifact.md`):
   positioned HTML sections. Step 1 (#392, done): the section language and its HTML → PPTX
   compiler (text, shapes, pictures, drawings, tables, charts, icons, transitions, build-ins), and
   a measurement against the SVG pages. Result, decision 0016: new slides stay SVG pages; a slide
   becomes a section when the user first edits it. Step 2 (#414, done): the SVG page → section
   converter (content unchanged) and decks that mix the two. The Slides panel, as the
   maintainer's mockups of 2026-10-17 draw it: read-only view, Present, Download and comments
   sent to coscribe (done, #420). Step 4, editing (#431): sections drawn by the server, the edit
   API, select/move/resize, text and the format bar, inserting, notes and properties, new slides
   and reorder, undo including coscribe's builds. Open from it: the user's edits and undos told to
   coscribe at the start of its next turn (design §12), and a human edit refused to be overwritten.
   Next: step 5, opening the user's own .pptx. The
   docx-preview actions are paused. A name for the user's own review actions in Settings is open;
   until then they carry the computer's user name.

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
- Secrets against a real Windows Credential Manager (scripted in `windows-more-checks.yml`;
  the Settings > Secrets screen stays by hand), and a real remote connector with a header from
  Settings > Secrets. The 20 checks for a person, with what is scripted: `docs/manual-checks.md`.
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
