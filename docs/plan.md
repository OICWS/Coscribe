# Plan: what is open now

Short on purpose: only what is still open, each with where to read more. What shipped lives in
[`docs/log/`](log/) (newest) and [`office-agent/ROADMAP.md`](../office-agent/ROADMAP.md) (short
index of the older history); why things are the way they are lives in
[`docs/decisions/`](decisions/) and [`ARCHITECTURE.md`](../ARCHITECTURE.md). Update this file in the
PR that changes the picture, and take a line out when its work is done; keep it under about 150
lines.

Last reviewed: 2026-11-18.

## Next, in order

1. **A more agentic coscribe, measured** (#819), each step scored by `office-agent/evals/agentic/`.
   Done: the evaluation (#820), the end-of-turn plan check (#821), the small model for side calls
   (#822), the delivery check of the Office files a turn wrote (#824), and, put before step 5 by
   the maintainer, a background script's end reported to its conversation (#826), Stop keeping the
   reply so far (#827) and a script moving to the background at its time limit or when the person
   writes mid-turn (`docs/log/2026-11-07-script-to-background.md`); a brief of what each folder
   holds (`docs/log/2026-11-08-folder-brief.md`) and an offer to save a job as a workflow or skill
   (`docs/log/2026-11-08-save-offer.md`); a connector the conversation offers on a card in the
   chat and the person connects in Settings (decision 0046, `docs/log/2026-11-11-connector-card.md`),
   the last of the plan's six steps. Next: the plan's measurements again on a model that does not
   pass every task already.
2. **Workflows** (#843; decisions 0028 to 0040, and 0042). Phases P0 to P5 are done
   (`docs/log/`, 2026-10-29 to 2026-11-02). Parallel steps are merged (#789, decision 0036
   proposed), and so are the simple view in words (#839, decision 0037) and the run page that
   says how it went before its steps (#840, decision 0038). A task that starts on something
   new in a connector is merged (#851, decision 0039), and so are the steps a run adds when a step
   fails at proactive or above (#861, decision 0042). Merged too: a task that starts on an event a
   program on the machine sends (#853, decision 0040), and a run asking before its models use
   more tokens, with nothing to set (#862, decision 0043), whose budget now counts llm steps'
   tokens (`docs/log/2026-11-15-llm-step-tokens.md`). A high or full step's agent hands parts of
   its task to sub-agents held to the step's rules (decision 0051,
   `docs/log/2026-11-18-workflow-step-sub-agents.md`). Open: adding steps when nothing failed.

3. **How turns go, measured in real use** (#867, decision 0045). Done: one line per turn in
   `turns.jsonl`, without the conversation's words (`docs/log/2026-11-10-turn-trace.md`), and
   eight agentic evaluation tasks replayed from recorded answers in the PR checks, the three that
   run a script with its recorded output (`docs/log/2026-11-10-eval-replay.md`,
   `docs/log/2026-11-10-plan-order.md`, `docs/log/2026-11-16-eval-script-tapes.md`); a sub-agent's
   run and a workflow agent step's pass counted too (`docs/log/2026-11-15-trace-subagent-turns.md`).
   A failed turn saved by the person as a file, which `evals/agentic/candidate.py` turns into a
   task to finish by hand (decision 0052, `docs/log/2026-11-18-failed-turn-export.md`).
   Next: a nightly replay of the three that write Office files.
4. **A workspace is a folder the person picks** (#926, decision 0048 proposed). Phases, one PR
   each: A the folder access card in chats and Settings' Folder access; B attachments and pasted
   pictures in `.coscribe/uploads/`; C the first start, no hidden default, environments and tasks
   moved over; D `.coscribe/settings.json` and `mcp.json`. A part 1 (the card in chats) is in
   `docs/log/2026-11-16-folder-access-card.md`; part 2 (Settings' environments table and the
   Allowed folders dialog, applied without a restart) is in `docs/log/2026-11-17-allowed-folders.md`.
   The edit dialog on one page, called a workspace in the UI, is in
   `docs/log/2026-11-18-workspace-dialog.md`. A browser level per site (decision 0050) is in
   `docs/log/2026-11-18-site-browser-levels-server.md`, `-desktop.md` and `-ui.md`. A task's
   reach (what it reaches, its folder inputs picked from it, a folder outside it allowed on the
   spot) is in `docs/log/2026-11-18-task-reach-server.md` and `-ui.md`. B is in
   `docs/log/2026-11-18-uploads-in-workspace.md`. C's server part (the first workspace) is in `docs/log/2026-11-18-first-workspace-server.md`.
   The first-start dialog is in `docs/log/2026-11-18-first-workspace-ui.md` (no chat-only
   conversation: the dialog has no skip, so Default always has a folder). D part 1 (settings and
   connectors wait for "Use them" and the file tools can't write them) is in
   `docs/log/2026-11-19-workspace-settings-trust.md`. D part 2 (an accepted `mcp.json` connects
   for that workspace's conversations) is in `docs/log/2026-11-19-workspace-connectors.md`, part 3
   (`settings.json`'s permissions decide gated calls) in `docs/log/2026-11-19-workspace-permissions.md`.
   A workspace reaches only the Allowed folders it picks (decision 0053); the server is in
   `docs/log/2026-11-19-allowed-folders-per-workspace.md`, the dialog's picker in
   `docs/log/2026-11-19-workspace-folder-picker.md`. Next: `settings.json`'s env, and the "Use them" card naming the settings and connectors.

## Open, smaller

- **A run's code is in a folder every contained run can write** (decision 0056, review on #1009):
  `script.py`, the Python wrapper and its guard config sit under `script-scratch`, which every
  run holds with `RX,W,D`, so one conversation's script can read or swap another run's code just
  before it starts and gain that run's folders and network. Write them to a folder only the
  server writes, granted read-only, and keep only TEMP under `script-scratch`.
- **Node's temp folder in the container** (`docs/log/2026-11-20-scratch-temp-delete.md`): Windows
  gives a contained Node run the container's own `AC\Temp` as TEMP, which Node's permission flags
  don't allow, so `os.tmpdir()` writes fail there. Python's `tempfile` is pinned to the scratch
  folder; Node could be pointed there the same way.
- **Leftover working files at the end of a turn** (`docs/log/2026-11-19-deck-record-paths.md`): the
  instructions ask the model to keep check files in a temporary folder, but nothing checks it, and
  files in `qa/`, `tmp/`, `scratch/` or a dot folder are hidden from the made-files list while they
  stay in the workspace. A turn-end check could name what the turn wrote there and is still present.

- **Connector credentials the redactor does not recognise** (`docs/log/2026-11-18-connection-string-passwords.md`):
  a scheme-less DSN (`user:pass@tcp(host)/db`), a password in an argument after a flag that does
  not name it, and a password under 8 characters printed on its own.

- **A reply's time after a reload** (`docs/log/2026-11-18-rewind-on-user-messages.md`): user
  messages keep their send time, replies don't, so a replayed reply's footer shows Copy alone.
  Needs a time on the AI message that no provider is sent.

- **Composer draft across pages:** opening Artifacts discards unsent text when the composer
  unmounts; reproduce/check noted in `docs/log/2026-11-18-artifacts-return.md`.

- **Code module manual checks** (#844): native patch approvals, the first download and the idle
  service exit are scripted without API keys; real-model behavior is not verified
  (`docs/log/2026-11-18-code-patch-approval.md`, `docs/log/2026-11-18-windows-checks-4-5-scripted.md`).

- **Compaction history:** bounded checkpoint reads and reconnect pagination are covered.
  The reported apparent change to an investigation title is not reproduced; confirm against
  the affected conversation (`docs/log/2026-11-17-compact-history-paging.md`).

- **Browser Context/form checks** (#932, #934): full-app popover visibility and genuine
  single-execution form batches are covered; authenticated SAP verification remains with
  the maintainer (`docs/log/2026-11-17-page-batch-input.md`).

- **Plan review** (#901): done (the model asks for review outside Plan mode; the person edits
  the task list in the Plan panel before accepting). Later: drag to reorder; `task_update`
  rewording or dropping a step, `task_create` taking several steps
  at once, and a background task started with the plan item it belongs to (the task card now
  guesses it from timing, which goes wrong when several items run at once;
  `docs/log/2026-11-15-plan-review-edits.md`).
- **Task list and a note sent mid-plan:** a new list starts once every task of the old one is
  done (`docs/log/2026-11-18-fresh-task-list.md`), but a note the person sends while a plan is
  still open joins that list if the model makes tasks for it. Whether such a note should get
  its own list is open.
- **Browser page lifecycle:** popup/source feedback, conversation-wide downloads and
  request cancellation have regression coverage. Native popup handles and focus/close behavior
  run in the Windows desktop smoke job; real-site verification remains outstanding
  (`docs/log/2026-11-16-browser-page-lifecycle.md`). Targeted concurrency, runtime workflow tab
  references, batch input and real draft progress are covered in #907; verify SAP exports and
  settings overlays on Windows (`docs/log/2026-11-16-browser-workflow-polish.md`).
  Browser abilities for conversations and saved workflows are planned in #915 (four parts);
  part 1, closing and reading several pages, is `docs/log/2026-11-16-browser-pages-batch.md`;
  part 2a, forms and page steps, `docs/log/2026-11-16-browser-forms.md`; part 2b, drag, file drop
  and the AI's clipboard, `docs/log/2026-11-16-browser-drag-clipboard.md`; part 3, tables to CSV
  across pages and pages to PDF, `docs/log/2026-11-16-browser-data-out.md`; part 4a, healing for the
  newer tools and the sign-in handover, `docs/log/2026-11-17-browser-sign-in-handover.md`; part
  4b, acting from a picture and watching a page, `docs/log/2026-11-17-browser-look-and-watch.md`.
  Open: which configured models take images (a text-only one refuses browser_screenshot's
  picture, as it does look_at_page's).

- **Docs:** a Doc still writes plans the brief did not give (a proposal's migration phases;
  `docs/log/2026-10-29-doc-writing-rules.md`). Version history for documents is wanted, not in v1.
  The Word panel is frozen (decisions 0025, 0027): its remaining items are dropped.
- **Artifacts:** pins are kept in the browser, not on the server; a scheduled run's files are not
  listed yet.
- **Startup cost** (#478 closed, `docs/metrics/2026-10-20-startup-cost.md`): `pptx`, `PIL` and
  `lxml` stay on the startup path (66 to 85 ms and 13 MiB, measured 2026-11-15; not worth
  editing every deck engine module). Open: the Windows numbers, cold start and the installed app
  (`scripts/measure_startup.py`, `office-agent-desktop/scripts/measure-startup.mjs`).
- **Scripts and commands:** a PyPI mirror setting for networks that block PyPI (#560); a company
  proxy on a real Windows machine (Basic only; NTLM and Kerberos are not supported, #666);
  another drive's `Users` folder hidden from commands, checked on a Windows machine with a second
  drive (decision 0049).
- **The `tools` interface** (#677): done; B was closed with a reason (#692): the `tools` card and
  `slice.py` list only the 54 names `tools` owns. Moving callers to the sub-components is not
  planned: it would first need `deep_imports` to count a declared sub-component as an entry, and
  the fresh-session samples found no wrong turn without it.
- **Structure leftovers** (closing report `docs/metrics/2026-10-19-structure-period-close.md`): the
  office formats' layers contract still ignores 3 imports (the pptx engine); golden files next for
  pptx templates and SmartArt edits, audio and CJK text, then `pdf` and `recalc_xlsx`; the layout
  of the Word open tasks 09 and 10.
- **PowerPoint, only when a real case asks:** checking names (people, companies) against the
  sources, not only numbers; lifting a slide back to SVG; a group's own rotate and scale.
- **Python lock** (`docs/log/2026-11-09-python-lock.md`): check the first weekly Dependabot
  `uv` pull request also moves indirect dependencies in `uv.lock`; `lockfile-only` was reported to
  move only direct ones (dependabot-core#14073). If it does not, a scheduled `uv lock --upgrade`
  job takes over that part.
- **minimatch alert #77** (`docs/log/2026-11-16-soupsieve-python-floor.md`): build-time only,
  through electron-builder, which still requires minimatch 10; move when it takes 11.
- **Scheduled runs:** a run whose turn is cancelled from outside (seen only through a test's time
  limit) is recorded as `completed`, because the turn swallows the cancellation
  (`docs/log/2026-11-15-windows-night-1110.md`). Whether a server shutdown does the same is not
  checked.
- **Design systems:** whether the model acts on the "no slide places the logo" warning is not
  measured: in the run of 2026-11-05 it placed the logo every time
  (`docs/log/2026-11-05-logo-and-assets-measured.md`).
- **Design canvas, the rest of the toolbar** (`docs/assessments/2026-10-29-design-and-dashboard.md`
  section 6.2; `docs/log/2026-11-16-design-present.md`): text, frame, pen and shapes on the
  canvas, and pages, need canvas elements beyond boards and notes in `.design.json`; an issue
  first, since the format changes.

- **Audit of 2026-11-10** (`docs/log/2026-11-10-audit-small-fixes.md` fixed five defects). Open:
  a provider's models read from its own list, and a first-run page that takes a compatible
  provider and checks the key; steps and time per task in the agentic evaluation.

- **Settings, after the simpler page** (`docs/log/2026-11-10-settings-simple.md`,
  `docs/log/2026-11-11-capability-switches-no-step-cap.md`). Open: the port for task events moves
  itself when 8790 is taken, and the listener's message stops naming a Settings row; a diagnostic
  log to export in place of Log level; a package a script needs installed from the chat, with
  approval; the models for code and for side jobs picked without a row; a proxy change that
  applies without a restart; with Artifacts off, "Make something new" still offers a Doc, a
  design and a dashboard, and a refused write still reads "Wrote" in the conversation.

## For the maintainer (settings and decisions)

- Add the Windows job's `pytest` to `main`'s required status checks (Settings, Branches). It has
  its 14 green scheduled nights (16 by 11-14; the red nights of 11-09 and 11-10 do not restart the
  count, `docs/log/2026-11-15-windows-night-1110.md`), and it now runs on every pull request
  (`docs/log/2026-11-15-windows-required.md`).
- Read the CodeQL alerts and the first `audit.yml` run.
- Decide whether changed-line coverage is enforced (`docs/assessments/2026-10-13-diff-coverage.md`).
- Decision 0036 (parallel workflow steps) is proposed with #789.
- A workflow run's pages stay open when it ends, so the person can check them (decided
  2026-11-16); a workflow that should clean up closes them in a step. A per-workflow "close pages
  when the run ends" setting is offered, not started (`docs/log/2026-11-16-browser-self-close-crash.md`).

## Needs the maintainer's testing (could not be verified here)

- Settings > Providers in the desktop app, and a key for one of the 12 new presets added end to
  end (no account for them here).

- The notices for made files on Windows: Open and Show in folder starting Excel and Explorer,
  and Copy putting a picture on the clipboard in the desktop app.

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

- Stop sometimes taking a while to end a turn on the maintainer's machine (#715): every stop
  path tried with fake models ends within 0.05 s (`docs/log/2026-11-15-stop-answers-the-page.md`);
  the exported conversation the issue waits for would show where the turn was.
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

- A tool that saves the browser page the model looks at as a picture file, so a screenshot it
  takes shows in the conversation and as a picture notice above the message box
  (`docs/log/2026-11-11-notice-kinds.md`). Today pictures there are only files it wrote.

- A workspace's uploads: saved in `.coscribe/uploads/<kind>/`, pictures from the message box
  included (`docs/log/2026-11-18-uploads-in-workspace.md`, `-pictures.md`); next a one-line
  description of each upload from the side model in `uploads/index.jsonl` (decision 0044, phase B of #926; the notes and skills
  shipped: `docs/log/2026-11-09-workspace-notes.md`). Later still: `workflows/` and
  `agents/` read from there, and notes coscribe writes by itself from a person's corrections.

- A scheduled task changed by describing the change in words, from the task page's Overview tab
  (#843): today a person edits steps in the Steps tab or asks in a conversation. Needs a
  route that drafts a revision of a saved task from a request, as a failed run's investigation does.

- The rest of `office-agent/README.md` (browser, MCP, hooks, Web UI, desktop) rewritten as the
  Files and Scripts sections were: what exists and where to read more, no copied parameters.

- A reasoning-effort choice for the user (#202): done (the scale and its mapping per model, the
  pill and slider, the evaluation on the same scale). Left: a look in the dark theme.
- The context panel: show the deferred system and MCP tools as their own rows (not counted in
  the window), and find why system tools read 38.2k at the start of a conversation while the
  bound tools measure about 4.9k tokens (`tests/tool_schemas.txt`).

- Require every review thread to be resolved before a pull request can merge (a ruleset
  setting): not needed at today's size; the maintainer decided on 2026-10-11 to wait.
- A second model family (Codex) reviewing invariant paths: when the second maintainer
  joins (decision 0009).

- A callback helper so a script can use a secret (needs its own local
  authentication).
- A terminal UI.
- Settings in Claude's grouping (2026-10-22): the code module under Capabilities (#537), and a
  Sessions category. Sessions has Prompt suggestions, background agents and archiving inactive conversations. Not built: a
  bypass-permissions gate (no such mode exists; a decision first). Desktop only, built: flash on
  attention and keep the computer awake while a turn runs (only the open conversation counts). Capabilities items that are not
  built: AI-powered artifacts, inline charts, a domain allowlist for the web tools.
