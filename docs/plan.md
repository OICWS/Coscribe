# Plan: what is open now

Short on purpose: only what is still open, each with where to read more. What shipped lives in
[`docs/log/`](log/) (newest) and [`office-agent/ROADMAP.md`](../office-agent/ROADMAP.md) (short
index of the older history); why things are the way they are lives in
[`docs/decisions/`](decisions/) and [`ARCHITECTURE.md`](../ARCHITECTURE.md). Update this file in the
PR that changes the picture, and take a line out when its work is done; keep it under about 150
lines.

Last reviewed: 2026-11-06.

## Next, in order

1. **Chat: a live Plan card** (maintainer, 2026-10-21 and 2026-11-06). Done: the conversation
   shows one task card under the latest call that changed the list, so it moves down only when its
   content changes, and it folds into a "N steps done" line when every item is done
   (`docs/log/2026-11-06-task-card-follows.md`). Open: the card no longer shows which background
   tasks an item started; bring that back on the card if it is missed.
2. **A more agentic coscribe, measured** (#819), each step scored by `office-agent/evals/agentic/`.
   Done: the evaluation (#820), the end-of-turn plan check (#821), the small model for side calls
   (#822), the delivery check of the Office files a turn wrote (#824), and, put before step 5 by
   the maintainer, a background script's end reported to its conversation (#826), Stop keeping the
   reply so far (#827) and a script moving to the background at its time limit or when the person
   writes mid-turn (`docs/log/2026-11-07-script-to-background.md`); a brief of what each folder
   holds (`docs/log/2026-11-08-folder-brief.md`) and an offer to save a job as a workflow or skill
   (`docs/log/2026-11-08-save-offer.md`). Next: an in-chat connector card (decision record and independent review first).
3. **Workflows** (#843; decisions 0028 to 0040, and 0042). Phases P0 to P5 are done
   (`docs/log/`, 2026-10-29 to 2026-11-02). Parallel steps are merged (#789, decision 0036
   proposed), and so are the simple view in words (#839, decision 0037) and the run page that
   says how it went before its steps (#840, decision 0038). A task that starts on something
   new in a connector is merged (#851, decision 0039), and so are the steps a run adds when a step
   fails at proactive or above (#861, decision 0042). In review: a task that starts on an event a
   program on the machine sends (#850, decision 0040), and a run asking before its models use
   more tokens, with nothing to set (decision 0043). Open: an L3 step delegating, adding steps
   when nothing failed, and counting llm steps' tokens.

## Open, smaller

- **Hidden issues:** when the suspended kurtosisOC account is restored, close its open issues as
  duplicates of #843 to #846 (`docs/log/2026-11-08-github-activity-pace.md`).
- **Docs:** a Doc still writes plans the brief did not give (a proposal's migration phases;
  `docs/log/2026-10-29-doc-writing-rules.md`). Version history for documents is wanted, not in v1.
  The Word panel is frozen (decisions 0025, 0027): its remaining items are dropped.
- **Artifacts:** pins are kept in the browser, not on the server; a scheduled run's files are not
  listed yet.
- **Startup cost** (#478, `docs/metrics/2026-10-20-startup-cost.md`): `pptx`, `PIL` and `lxml`
  loaded lazily once the sections modules may be edited; the sidecar started earlier in the
  Electron shell.
- **Scripts and commands:** a PyPI mirror setting for networks that block PyPI (#560); hiding other
  drives' user folders from commands (#845); a company proxy on a real Windows machine (Basic only;
  NTLM and Kerberos are not supported, #666).
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
- **Design systems:** whether the model acts on the "no slide places the logo" warning is not
  measured: in the run of 2026-11-05 it placed the logo every time
  (`docs/log/2026-11-05-logo-and-assets-measured.md`).

## For the maintainer (settings and decisions)

- Make the Windows job required once it has 14 green scheduled nights; the count restarted on
  2026-10-27.
- Read the CodeQL alerts and the first `audit.yml` run.
- Decide whether changed-line coverage is enforced (`docs/assessments/2026-10-13-diff-coverage.md`).
- Decision 0036 (parallel workflow steps) is proposed with #789.

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

- A scheduled task changed by describing the change in words, from the task page's simple view
  (#843): today a person edits steps in the detailed view or asks in a conversation. Needs a
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

- Conversations reading and messaging each other (records 0008 and 0023, built: every non-archived conversation is reachable; the Edit environment dialog still has its old messages section until the redesign in issue 560 lands).

- A callback helper so a script can use a secret (needs its own local
  authentication).
- A terminal UI.
- Settings in Claude's grouping (2026-10-22): the code module under Capabilities (#537), and a
  Sessions category. Sessions has Prompt suggestions, background agents and archiving inactive conversations. Not built: a
  bypass-permissions gate (no such mode exists; a decision first). Desktop only, built: flash on
  attention and keep the computer awake while a turn runs (only the open conversation counts). Capabilities items that are not
  built: AI-powered artifacts, inline charts, a domain allowlist for the web tools.
