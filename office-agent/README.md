# Coscribe

[![coscribe CI](https://github.com/OICWS/project/actions/workflows/office-agent-ci.yml/badge.svg)](https://github.com/OICWS/project/actions/workflows/office-agent-ci.yml)

Local, user-friendly agentic system for office work. Agent runtime and
model access go through [LangGraph](https://github.com/langchain-ai/langgraph)/
[LangChain](https://github.com/langchain-ai/langchain) (`runtime_lg/`) --
the project's original foundation, aisuite, is no longer a dependency. See `../ARCHITECTURE.md`
for the full design and `runtime_lg/README.md` for why/how that changed.

A single Coordinator agent with built-in file, document/spreadsheet/
presentation, task-tracking, Skill, and subagent-delegation tools, plus
optional MCP server tools and Hooks -- runnable from the CLI (`coscribe`)
or a full web UI (`coscribe-web`), with Claude Code's four permission
modes -- Manual, Accept Edits, Plan and Auto -- switchable mid-session.

## Setup

```bash
cd office-agent
python3 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev,web]"
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY,
# and COSCRIBE_DEFAULT_MODEL as "provider:model" (e.g. gemini:gemini-2.5-flash)
cd frontend && npm install && npm run build && cd ..
# ^ one-time (and after any frontend change) -- compiles into
# src/coscribe/web/static/, which coscribe-web serves and which is
# gitignored (a build artifact, not source) so a fresh checkout has none
# yet. Needed for coscribe-web; not needed for the CLI-only `coscribe`.
```

**In plain terms:** Coscribe talks to three model makers directly --
Anthropic (Claude), Google (Gemini), and OpenAI (GPT). Beyond those
three, it can also connect to any other service that offers an
"OpenAI-compatible" API -- a specific, common interface format that
vendors like DeepSeek, Kimi, and Zhipu GLM (and local model runners like
Ollama) choose to support, precisely so tools built for OpenAI work with
them with no changes. This is *not* "compatible with any one of the
three" -- it specifically means speaking OpenAI's own format; there's no
equivalent "Anthropic-compatible" or "Gemini-compatible" API that other
vendors offer today, so that's not a path into Coscribe the way
OpenAI-compatible is.

Supported model prefixes: `anthropic:`, `openai:`, `gemini:` (Gemini Developer
API — a plain API key from https://aistudio.google.com/apikey, not Vertex AI).
Every real conversation turn goes through `langchain-google-genai`/
`langchain-anthropic`/`langchain-openai` (published packages, not vendored
code) via runtime_lg's `resolve_chat_model`. The context-usage bar's max-size
lookup asks the Gemini API directly (`runtime/llm_client.py`) and estimates for the rest.

Any other OpenAI-compatible API (DeepSeek, Kimi/Moonshot, Zhipu GLM, or
anything else) can be added as a custom provider prefix -- see
[Custom LLM providers](#custom-llm-providers) below.

## Run

```bash
coscribe
```

This starts an interactive REPL backed by a real LLM call (per
`COSCRIBE_DEFAULT_MODEL` in `.env`). The Coordinator can list/read/search
files under `COSCRIBE_WORKSPACE_ROOT` (defaults to `./workspace`).

The built-in file/document/spreadsheet/presentation tools can also reach
specific directories outside the workspace, if you configure them. In the
web UI, Settings > Workspace has a unified **Directories** list: Workspace
Root always sits at the top (always fully readable and writable), and you
can add any number of additional directories below it, each with its own
Read only / Read & Write toggle -- type a path directly or use **Browse...**,
backed by a small server-side folder picker (`/api/browse-dirs`), not the
browser's native file picker, which never exposes a selected folder's real
absolute path for security reasons; this sidesteps that by listing real
directories on your machine directly. This is useful for, say, letting the
Coordinator read a file a browser-automation MCP server just downloaded,
without first copying it into the workspace by hand.

A conversation can also have its own folders: **Add folder** under the
message box attaches any number of them, and they can be removed or added
between replies. The first is the main one (relative paths resolve there);
the agent can read and write in all of them. A conversation with none uses
the Workspace Root.

Under the hood this is still two `.env` variables --
`COSCRIBE_EXTRA_READABLE_DIRS` (read-only) and
`COSCRIBE_EXTRA_WRITABLE_DIRS` (read+write; a writable directory doesn't
need to also be listed as readable) -- each a comma-separated list of
absolute paths, e.g.
`COSCRIBE_EXTRA_WRITABLE_DIRS=/home/you/Downloads,/home/you/Documents`,
for when you'd rather edit `.env` directly than use the directories list.

`COSCRIBE_MAX_TURNS` (`.env`, default `20`) caps how many tool-calling
turns a single agent loop runs before giving up, to bound token/time spend
from a loop that keeps calling tools without finishing -- applies to a
normal chat turn and to each scheduled-task run; `spawn_agent`/
`review_work` sub-agents use their own smaller, separate default (6), not
this setting. Editable from the web UI's Settings > General as well as
`.env` directly.

Session state is persisted to `.coscribe/state/<thread-id>.json` so a
conversation can be resumed with `coscribe --thread <thread-id>`.

For multi-step requests, the Coordinator can plan and track progress with
`task_create`/`task_update`/`task_list`, persisted per-thread alongside the
session state at `.coscribe/state/<thread-id>.tasks.json`.

Several commands are typed as a message mid-session (not startup flags):

The permission modes follow Claude Code's
(code.claude.com/docs/en/permission-modes). One is on at a time; typing a
mode's command again returns to **Manual**, which asks before every
change, script or outside action. A new conversation starts in **Auto**,
as Claude Code does; change that under Settings > General > Default Mode
(`COSCRIBE_DEFAULT_PERMISSION_MODE`: `manual`, `accept-edits`, `plan` or
`auto`, applied to new conversations without a restart). A scheduled
task's run follows the task's own approval setting instead.

- `/accept-edits` -- Accept Edits: file edits in the conversation's folders
  (and other local changes: `WRITE_LOCAL` tools) run without asking; running
  code (`EXEC`) and acting outside this computer (`EXTERNAL`) still ask.
- `/plan` -- Plan: only read-only and task-tracking tools run; everything
  else is refused, no prompt. When the plan is ready the model calls
  `exit_plan_mode(plan)`, and the chat shows it with Claude Code's three
  choices: **Yes, and use auto mode**, **Yes, manually approve edits**
  (Manual), or **No, keep planning** with what to change. Approving leaves
  Plan mode.
- `/auto` -- Auto: a reviewer model (`runtime_lg/auto_review.py`, the
  conversation's own model) decides each gated call in the user's place. It
  allows ordinary work in the conversation's folders and blocks what's hard
  to undo or leaves the computer -- running downloaded code, sending files
  or data out, deleting or overwriting files that were there before,
  acting in the user's accounts -- unless the user asked for that specific
  action; a stated boundary ("don't email anyone") blocks too. A blocked
  call is refused back to the model with the reason. After 3 blocks in a
  row or 20 in all, or when the reviewer gives no usable answer, the user
  is asked instead, with a note saying why; approving resumes Auto. With
  nobody watching (a self-wake turn), the reviewer still decides, and what
  would have been asked is refused instead. Hooks and exec-policy rules
  still come first, as in every mode.
- `/compact` -- summarize the current thread's message history down to a
  single note, freeing up context for the rest of a long-running session.
  Does nothing if there's not much yet to compact. This also happens
  automatically once a turn's usage crosses `COSCRIBE_AUTO_COMPACT_THRESHOLD`
  of the model's context window (default 0.8) -- see
  [Scheduled / unattended runs](#scheduled--unattended-runs) below for why.
- `/clear` -- wipe the current thread's conversation history outright and
  start fresh (unlike `/compact`, which summarizes rather than discards).
  Doesn't touch Plan Mode/Accept Edits Mode (those are session-level
  toggles, not conversation content) or memory/tasks/scheduled tasks.
- `/saveworkflow [name]` -- turn what this conversation just did into a
  reusable workflow. In the web UI this drafts a
  [workflow](#workflows----fixed-steps-instead-of-a-prompt) (fixed steps,
  not a prompt) for review before anything is saved; the name is
  optional. In the CLI the model still distills the conversation into a
  prompt-backed [scheduled task](#scheduled-tasks----a-real-product-level-scheduler)
  draft.
- `/stop` -- stop the current in-progress run (a runaway tool-calling loop,
  a task stuck retrying, or just a response you no longer need). In the
  web UI, this is also what the composer's send button turns into while a
  run is in flight -- click it (or type `/stop`) to cancel. Unlike the other
  commands here, it doesn't wait its turn behind whatever's currently
  running: it reaches into that run directly, denying any tool call it's
  currently waiting on approval for. The run ends with whatever partial
  progress it had already made; nothing already-executed is undone. Web UI
  only -- the CLI's REPL has no way to accept a `/stop` while it's blocked
  waiting on the current turn.
- `/init` -- have the Coordinator explore `COSCRIBE_WORKSPACE_ROOT` and
  write a project overview to `OVERVIEW.md` at its root, analogous to Claude
  Code's own `/init`.
- `/<skill-name>` -- invoke a loaded skill directly by its name (e.g.
  `/pdf-extract summarize report.pdf`), splicing its full instructions
  straight into that turn instead of relying on the model to notice it's
  relevant and call `load_skill` itself. Anything typed after the name is
  passed along as the request. A `/word` that matches neither a built-in
  command nor a skill name is rejected locally with no LLM call, rather than
  sent through as plain text.

### Scheduled / unattended runs

The intended pattern for a repeating task: develop and validate it
interactively first (with the normal approval gate on risky tool calls),
then hand the *same thread* off to an external scheduler (cron, systemd
timer, ...) that re-invokes it on a schedule, reusing `--thread` so it
keeps its accumulated context across runs.

```bash
coscribe --thread nightly-report --accept-edits \
  --message "Build tonight's sales report from sales/today.xlsx."
```

(For most repeating tasks, the built-in [Scheduled
Tasks](#scheduled-tasks----a-real-product-level-scheduler) below is the
simpler route -- no cron entry, and each run gets its own conversation.)

- `--message`/`-m TEXT` -- send one message non-interactively and exit,
  instead of starting the REPL. Output is exactly the model's final reply
  (nothing else), and the exit code is nonzero if the call errored or hit
  the turn limit -- both meant for cron/systemd logs and alerting. Slash
  commands (`/plan`, `/init`, skill names, ...) are **not** interpreted in
  this mode; the text is sent to the agent as-is.
- `--accept-edits` -- start in accept-edits mode from the first turn.
  Without it, `-m` still works, but any tool call that needs approval will
  hang waiting on a prompt nothing unattended can ever answer -- combine
  the two for a real scheduled job.
- `COSCRIBE_AUTO_COMPACT_THRESHOLD` (`.env`, default `0.8`) -- since a
  thread reused by every scheduled run would otherwise grow forever with
  nobody present to type `/compact`, it's compacted automatically once a
  turn's token usage crosses this fraction of the model's context window.
  Set it above `1.0` to disable and rely on manual `/compact` only.

### Sleep and wake -- pausing a conversation instead of scheduling a new one

The pattern above works well for a task that runs on a fixed external
schedule. For a task where the *agent itself* decides when to check back
-- "wait until 9am tomorrow," "resume once that background script
finishes," "resume once something else tells you to" -- the Coordinator
has its own tools instead of you writing a second cron entry per task:

- `sleep_until(wake_at, reason)` / `sleep_for(seconds, reason)` -- pause
  this conversation and automatically resume it at a wall-clock time or
  after a delay.
- `wake_on_task(task_id, reason)` -- pause until a specific in-progress
  background script (started via `run_background_script`, see below)
  finishes (`task_id` is that task's id).
- `wake_on_event(event_key, reason)` / `signal_event(event_key, payload)`
  -- pause until a named event fires; `signal_event` is how another turn
  (this thread, another thread, or a future connector/webhook) fires it.
- `list_wakes()` / `cancel_wake(wake_id)` -- see or cancel this
  conversation's own pending sleep/wake requests.

Resuming needs *something* to periodically check whether a pending
sleep/wake is due and, if so, restart that thread with a synthetic
"scheduled wake-up reached" message. Two ways to get that:

- **Run `coscribe-web`.** While it's running, it checks for due wakes
  automatically every `COSCRIBE_WAKE_POLL_SECONDS` (`.env`, default `30`)
  -- nothing else to configure.
- **Schedule `coscribe --check-wakes`** via external cron/systemd (e.g.
  every 5 minutes) if you'd rather not keep the web server running. It
  checks every thread once, resumes whichever have a due wake, prints a
  one-line summary per thread it resumed, and exits -- the generic,
  agent-driven counterpart to hand-writing a fixed-time `--message` cron
  entry per scheduled task.

A tool call that needs approval during a wake-triggered turn is left
pending, same as an unattended `-m` run made without `--accept-edits` --
there's nobody there to answer it, so it waits durably until you next open
that thread. If a browser tab already has the thread open live when a
background poll resumes it, the reply is saved correctly but won't stream
into that open tab in real time -- you'll see it on the next reload or
reconnect, not pushed live (see `ARCHITECTURE.md` for why).

### Scheduled Tasks -- a real, product-level scheduler

Both patterns above still need *something*: an external cron entry, or a
conversation already open to call `sleep_until`/`sleep_for` from. Scheduled
Tasks is the built-in alternative that needs neither -- a named,
independently-managed trigger that runs once at a future time, or daily/
weekly/monthly, entirely on its own.

A scheduled task is also what Coscribe calls a **workflow**: a name, a
standalone prompt describing the work, and a schedule -- hourly, daily,
weekdays, weekly, monthly, or "manual" (runs only when you click **Run
now**). There's no separate recording/replay format; the prompt *is* the
workflow.

**Creating one starts in conversation.** Work the task out in chat first,
then ask for it to be saved. The
Coordinator calls `create_scheduled_task`, which doesn't save anything by
itself -- it drafts the task, and the web UI shows a review card that
opens the task form prefilled with the model's draft: you edit any field,
then save or dismiss, and the model is told which. An unattended turn
(nobody to review) never creates a task. The Scheduled page's **New task**
menu has the same two routes: **Create with Coscribe** (a new chat,
prefilled to describe the task) or **Set up manually** (the blank form).

- `create_scheduled_task(name, kind, at, prompt, weekday=None, day_of_month=None, start_date=None, model=None, approval_mode="manual")`
  -- drafts a task for review, as above. `kind` is `"manual"` / `"hourly"`
  / `"daily"` / `"weekdays"` / `"weekly"` / `"monthly"`; `at` is `"HH:MM"`.
  `weekday` (0=Monday..6=Sunday) is required for `"weekly"`,
  `day_of_month` for `"monthly"` (clamped to a short month's real last
  day). The CLI asks `y/N` in place of the review form.
- `list_scheduled_tasks()` / `pause_scheduled_task(trigger_id)` /
  `resume_scheduled_task(trigger_id)` / `delete_scheduled_task(trigger_id)`
  -- manage every scheduled task, not just ones the current conversation
  created. Resuming recomputes the next run time from *now*, so a task
  paused for a week doesn't fire a backlog of missed runs.

**Every run is a fresh conversation** (`scheduled-<trigger_id>-<run_id>`),
never the thread the task was created from and never a previous run's --
so runs don't accumulate each other's context, and one run's mess can't
leak into the next. A run's conversation opens with a "Ran scheduled task"
card showing the exact instructions it got; the breadcrumb above it
switches between that task's runs. Each task keeps its last 50 run records
(older ones are pruned, their conversations deleted with them); deleting a
task deletes all of its run conversations too.

**Notes carry memory between runs** (on by default; per task, "Remember
between runs" on the task page). Every run is shown the task's current
notes at the start of its prompt and asked to rewrite them before it
finishes, via `update_task_notes(notes)` -- a tool that only exists inside
a run's own conversation. Progress markers ("processed through row 480"),
what changed, pitfalls worth remembering. You can read and edit the notes
yourself on the task page (`GET`/`PUT /api/scheduled-tasks/{id}/notes`);
they're stored next to the task as `<trigger_id>.notes.md`, capped at 4000
characters.

**Run now** starts a manual run and returns immediately -- the browser
opens the run's conversation and streams it live while it runs in the
background; closing the tab doesn't stop it. A manual run never touches
the regular schedule (running a daily 9am task by hand at 2pm doesn't
skip tomorrow's 9am fire, and a paused task stays paused).

Firing shares the sleep/wake poll above -- `coscribe-web`'s background
poll (every `COSCRIBE_WAKE_POLL_SECONDS`) and `coscribe --check-wakes`
both check for due scheduled tasks in the same pass, no separate flag or
server to run. A due task's schedule advances when its run *starts*, so a
slow run is never started twice and a failed run isn't retried every poll
(its failure is on the run record). Due runs execute concurrently. Times
are the machine's own local wall-clock time -- Coscribe is single-user,
local-first software with no per-user timezone concept.

Each run ends with a status on its record: `completed`, `failed` (with
the error), `stopped`, or `needs_approval`. Each task's **Permissions**
decide which tool calls a run may make without asking anyone, by risk
tier (see `ARCHITECTURE.md`'s risk taxonomy):

| Permissions | `WRITE_LOCAL` (create/edit local files) | `EXEC` (run scripts) / `EXTERNAL` (MCP connectors, downloads) |
|---|---|---|
| Ask before every action (`"manual"`, default) | asks | asks |
| Automatically approve (`"auto"`) | approved | asks |
| Never ask (`"skip"`) | approved | approved |

"Asks" never blocks a run: the call parks durably in the run's
conversation, the run ends as `needs_approval`, and the approval is
offered the next time you open that run (or right away, if you're
already watching it). Resolving it finishes the run under the same
permissions and updates its record. Under every tier, your own blocking
rules still win: a PreToolUse hook veto or an exec-policy `forbidden`
rule rejects the call. Every automatic approval is recorded in the audit
log (`approval_mode_auto` / `approval_mode_skip`). If Coscribe exits
mid-run, that run is marked `failed` on the next start.

### Workflows -- fixed steps instead of a prompt

A scheduled task can hold a **workflow** instead of a prompt: named
inputs plus an ordered list of low-autonomy steps, run by a LangGraph
graph (`src/coscribe/workflows/`). Where a prompt task hands the whole job
to the model each time, a workflow only lets a model decide where a step
says so, and checks what comes out -- for the repeatable, auditable work
(month-end reconciliations, report roll-ups) a free-form agent is too
variable for.

| Step | Model? | What it does |
|---|---|---|
| `tool` | no | Calls one built-in tool with fixed arguments; `{{name}}` references fill in earlier values. |
| `script` | no | Runs a fixed Python script, reviewed once when saved. Earlier values arrive as an `inputs` dict (injected as data, never spliced into the code); the result is the JSON its last output line prints. |
| `llm` | one call, no tools | Returns exactly the declared fields (`text`/`number`/`boolean`/`list`) at temperature 0. A wrong answer is sent back once with what was wrong, then the step fails. Uses forced structured output where the provider allows it, else asks for bare JSON (DeepSeek's thinking mode refuses forced tool calls). |
| `check` | no | Structured comparisons (`eq`, `ne`, `gt`, `ge`, `lt`, `le`, `contains`, `not_empty`) on references, counts (`{"count": "matches"}`) or literals. Any that fails stops the run, recording what it compared. |
| `approval` | no | Pauses until a person approves -- only when its `when` condition holds, if it has one. |
| `branch` | no | Runs its `then` steps when a condition holds, else its `otherwise` steps. |
| `loop` | no | Runs its steps once per item of a list, in order, with the item as `{{item}}` (or the name you give it); `collect` keeps one value per pass, saved as a list. A list longer than `max_items` (default 50, at most 200) stops the run instead of being cut short. |

References are checked when the workflow is saved -- a typo, or reading
a value a later step produces, is refused with the step named (`step 3
('Has words') reads 'taly.words', which isn't an input or the result of
an earlier step`). A saved workflow's tool and script steps run without
per-call approval prompts (the task's Permissions apply to prompt tasks):
saving it is the review. Only `approval` steps pause.

Branches and loops scope what they produce. After a branch, a name is
readable only if both arms produce it (that's how a value set either way
is merged); a loop's item and the names made inside it exist per pass, so
only its collected list is readable after it -- and two loops in a row
can both call their item `item`. Steps are numbered in document order,
nested ones included, in messages, the editor and the run view. Blocks
nest at most three deep; a workflow has at most 100 steps in all. Reading
a model step's field it doesn't declare (`summary.text` when it returns
only `summary`) is refused at save time too.

Every step's status, timing, output (trimmed) and check results are
recorded on the run as it goes. A run that stops can be taken further:

- `POST /api/scheduled-tasks/{id}/runs/{run_id}/retry` -- re-run from the
  failed step, or from an earlier `step_id` (a check failing because a
  model step returned bad data needs that model step re-run). Steps
  before it aren't re-run: their results come from the run's checkpoint.
- `POST .../runs/{run_id}/answer` with `{"approved": true|false,
  "note": ""}` -- answer a pending approval step. Declining fails the run
  there; retrying that step asks again.

`POST /api/scheduled-tasks/{id}/run` takes optional `{"inputs": {...}}`;
an input left out uses its default. The PDF audit used to verify this is
`tests/fixtures/pdf_error_audit_workflow.json`.

In the web UI, a workflow task's page shows its **inputs** and its
**steps** as a vertical list -- a colored tile per kind, a one-line
summary per step in which values read from inputs (tinted) or earlier
steps (neutral) appear as tokens. Opening a step edits its name and its
kind's own fields: tool arguments, the script, a model step's
instructions, returned fields (type, meaning) and model, a check's
comparisons and literal values, an approval's message and condition.
Each step saves on its own; the server re-validates the whole workflow,
and a refusal shows under that step. **Run now** asks for the inputs
first, prefilled with their defaults.

Building one from scratch: **New task → Build a workflow** creates a task
with no steps (it won't run until it has some) and opens its page. The
**+** between steps (or **Add step** at the end) picks a kind; a tool
step then picks from every built-in and connected tool, searchable, and
gets a form from that tool's own parameters -- types, defaults, required
marks and each argument's meaning from its docstring (`GET /api/tools`
now includes `params`). A check's operands can be a value, a count of
one, or a fixed text/number/yes-no, with the names available at that
point suggested (model steps' fields included). Inputs are edited in
place too. An open step can be moved up or down or deleted; the server
refuses an edit that would leave a step reading something that no longer
comes before it, and says which ("Can't move it there -- step 2 ('Check
the values') reads 'result.q1_total', which isn't an input or the result
of an earlier step"). Renaming a step's result, or an input, rewrites
every later reference to it, so a rename never breaks the steps after.

A workflow run opens as a timeline instead of a conversation: each step's
status, duration and result (a model step's fields as a table, search
hits as rows), updated live as steps finish. A failed step says exactly
what went wrong -- for a check, each comparison with what it found
(`6 ≠ 5`) -- and offers the way on: **Retry this step**, or, when a check
rejected data a model step produced, **Retry from step N** on that model
step; **Edit step N** opens that step on the task page. An approval step
waits as a card with its message, an optional note (kept on the run) and
Approve / Decline. The header names where a run stopped ("Stopped at
step 3"), and the side panel's Progress follows the steps.

In the editor a branch or loop is a card that holds its own lists --
**Then** / **Otherwise**, or **For each** -- each with its own **Add
step** and **+** between steps; a step moves up or down within its list.
Deleting a block says how many steps inside it go too. In a run, a branch
shows the arm it took and the other as "not taken"; a loop shows one
item's pass at a time, with a numbered, colour-coded strip to pick any
item (failed and waiting passes stand out) and the item's own name. A
step failing inside a loop stops the run at that pass: **Retry this
step** (or **Retry from step N**) re-runs from there, on that pass, and
the passes before it are kept, not re-run.

**From a conversation.** Once a conversation has done a task with tools,
**Save as workflow** at the bottom of the side panel (or `/saveworkflow
[name]` in the composer) drafts a workflow from it
(`src/coscribe/workflows/solidify.py`, `POST
/api/threads/{id}/workflow-draft`). A curator model reads the
conversation -- each tool call numbered, with its real arguments and a
trimmed result, failed calls marked -- and keeps only the calls that did
the work: copied arguments, the values that change from run to run
turned into inputs (the original as default), `run_python_script` calls
as script steps, judgment as model steps, and checks grounded in what the
conversation verified. Its reply is held to the same save-time rules plus
the real tool catalog (the tool exists, takes those arguments, has its
required ones); a draft that fails goes back with the problems, up to
three tries. The draft opens in the step editor with the curator's
**Worth checking** notes (guesses, values it made inputs, steps it
dropped); edits are validated (`POST /api/workflows/validate`) but not
saved, and **Save as task…** picks when it runs. Nothing is saved until
then.

The chat model can do the same when asked in plain words ("make this a
fixed workflow I can rerun"): its `draft_workflow` tool runs the same
curator on the conversation so far, and the result shows in the chat as
a **Fixed workflow draft** card -- step tiles, inputs, the number of
things worth checking -- whose **Review and save** opens the draft page.
Unless the user already said which kind, the model asks ("Fixed steps"
or "Written instructions") before drafting either.

**Changing a saved task from chat.** Asked to change a task that already
exists, the model changes it in place rather than drafting a copy:

- `revise_workflow(task_id, request)` for a fixed workflow's steps. A
  reviser model gets the saved workflow, the request and the conversation,
  changes only what the request needs (other steps and ids kept), and is
  checked like a new draft; tools it adds that it wasn't shown come back
  with their parameters on the retry. The chat shows a **Workflow
  changes** card listing each change; **Review changes** opens the step
  editor with a "What changes" list, and **Save changes** replaces the
  workflow on the same task.
- `edit_scheduled_task(trigger_id, ...)` for the instructions, name,
  schedule, model or approval setting. The review opens the task's edit
  form filled in with the whole task as it would be saved.

Either way the task keeps its runs and notes, and nothing changes until
the user saves.

**Tested before review.** A fixed workflow runs without a model deciding
anything; the assistant works outside the run. After drafting, it runs
the draft once for real with `test_workflow` (every step, stopping at the
first failure or before an approval step), fixes what failed with
`revise_workflow(draft_id=...)` and tests again, at most 3 rounds, then
says whether the last test passed. The draft card leads with that
result: passed or failed at which step, the files the steps wrote (rows x
columns for xlsx/csv), and a screenshot of the page the test ended on.
The newest unsaved draft stays pinned at the bottom of the conversation
while its card is out of view.

**When a run fails.** The run stops there -- nothing after the failed
step produces data -- and its page shows the step, the error and a
screenshot of the page at that moment. **Let AI look into it** (with the
default model or one picked beside it) opens a new conversation that
reproduces the failure with `test_workflow(task_id=...)`, finds the
cause, and drafts a tested revision for the user to save; it never saves
anything itself. A task's **Look into failures automatically** switch
does this on its own after a failed run (reproducing the task's steps
without asking; anything else still waits for the user). A running run
can be stopped from its page; a stopped run is recorded as stopped, not
failed.

**Notifications** (desktop app): when a task run finishes -- "Completed
· 448 rows · saved to exports/...", "Failed -- <step>: <error>", or
waiting for the user -- set to All, Problems only or Off in Settings >
General. Clicking one opens the run, or the conversation looking into it.

**Connector tools in steps.** A tool step can call a connected
connector's (MCP) tools, not only built-in ones -- the Office 365
connector's, for example, so a task done once in chat can become fixed
steps. Their parameters come from the tool's
JSON schema (the editor's argument form and the curator's tool list use
them); their text replies become values (JSON decoded, and for replies
laid out as `### Result` / `### Ran Playwright code` sections, the
Result section). The curator is told not to copy element references from
page snapshots (`ref: "e42"`), which change on every load, and to act
through selectors or page scripts that worked instead. A connector that
isn't connected when a run starts stops it before any step runs.

**A task's workspace.** A task can have its own folder (the folder
button in the task form; `workspace` in the API, which must be an
existing folder): its runs read and write there instead of the app's
default workspace. A task saved from a conversation starts with that
conversation's folder.

## Files, documents and artifacts

Each tool's parameters and contract live in its own docstring, which is also what the model reads:
`tests/tool_schemas.txt` lists every tool, its risk tier and whether it is bound or found through
`search_tools` (decision 0001). How coscribe should go about a kind of work lives in the built-in
skills (`src/coscribe/builtin_skills/<name>/SKILL.md`). This section only says what exists and
where to read more.

- **Files.** `list_files`, `search_files`, `read_file`, `get_file_info` (`READ`) and `write_file`,
  `edit_file`, `edit_file_batch`, `move_file`, `copy_file`, `delete_file` (`WRITE_LOCAL`, a delete
  goes to the recycle bin) work inside the conversation's folders (Settings › Workspace; a
  conversation can be given more, read-only or read-write). Card: `src/coscribe/tools/AGENTS.md`.
- **Artifacts** (decisions 0015, 0027): what coscribe makes from a source it owns opens in a panel
  beside the conversation and is listed on the Artifacts page, where it can be renamed, copied,
  pinned and deleted.
  - *Doc*: a markdown document edited in the app, with comments for coscribe, exported to
    Markdown, PDF and Word (decision 0025; the Docs skill).
  - *Slides*: a deck written as one SVG page per slide, compiled by `build_pptx_from_pages` into
    native, editable PowerPoint; a slide becomes an HTML section the first time it is edited in
    the panel (decisions 0010, 0016-0018, 0020; the PPTX Pages skill, `PPTX_DESIGN.md`).
  - *Design*: a canvas of HTML artboards with shared variables, panned, zoomed and played in the
    panel, its artboards linked into clickable prototypes (the Design skill).
  - *Dashboard*: a page and its datasets; every figure shows where it came from, and Refresh asks
    coscribe to read the sources again (the Dashboard skill).
  - `look_at_page` lets coscribe see a Design or Dashboard as the app draws it, with a report of
    what a look catches.
- **Office files the person brings** are read with `read_docx`, `read_xlsx`, `read_pptx` and
  `read_pdf`, and changed with the format's own tools: Word through `write_docx`,
  `edit_docx_structure` and the review tools (tracked changes, comments; the Word skill), Excel
  through `write_xlsx_cells` and `modify_xlsx` with formulas computed by IronCalc (decision 0011;
  the Excel skill), PowerPoint through `write_pptx` and the template and shape tools for the
  person's own template (the PPTX Slides skill). They are shown, not owned: the Word panel is frozen
  and an Excel file is not an artifact (decisions 0025, 0027).
- **Previews and conversion** use the Microsoft Office or WPS on the machine through COM; a PDF
  and a deck built from SVG pages need no office program, and LibreOffice is an optional engine,
  found or installed on request (decisions 0012, 0026). Without one, a preview or conversion is
  skipped with a reason, never the write.

## Scripts and commands

`run_python_script`, `run_node_script` and `run_background_script` run code the model writes, in a
Python venv and an npm directory of their own (Settings › Capabilities installs packages and
chooses the Python); `run_background_command` runs a command line. All are `EXEC` and approved
under the permission mode.

- On Windows, where the machine passed the self-test, scripts run in an AppContainer that reaches
  only the conversation's folders (read-write folders without delete) and the interpreter
  (decision 0021). Where it failed, scripts are refused unless the person lets that conversation
  run without isolation, which is recorded.
- Command lines run in Codex's Windows sandbox once Settings › Capabilities set it up
  (decision 0022): they write only the conversation's read-write folders, are offline unless the
  environment's network is Full, and the person's private folders are hidden by default. Without
  it, a command runs as the user only after the person allowed that, and each one is approved.
- Off Windows, or let out of isolation, code runs as the user; a folder guard then catches
  mistaken writes and is not a security boundary.
- A script starts from an allow-list of environment variables, never the server's own (which holds
  the provider keys). Card: `src/coscribe/tools/exec/AGENTS.md`.

## Web search

`web_search(query, max_results=5)` queries the live web through the
`ddgs` package (no API key required) -- for grounding (current events,
facts to verify, anything beyond training data), not document retrieval.
It's a separate thing from `search_files`/`search_pdf`, which only ever
look at files already in the workspace; use `web_search` when the answer
genuinely isn't something already on disk or already known. Returns a
list of `{"title", "url", "snippet"}` per result. Low risk, no approval
required -- it only reads from the public web, no side effects.

Uses `ddgs`'s own `"auto"` backend mode -- queries several free,
no-API-key engines (DuckDuckGo, Brave, Google, Mojeek, Startpage,
Wikipedia, Yahoo, Yandex) and returns whichever results come back, rather
than being pinned to one. This isn't just theoretical resilience: an
earlier version pinned to DuckDuckGo alone, and a real user hit
DuckDuckGo's own anti-bot response (an HTTP 202 with no real results)
returning an empty search for a live query -- switching to `"auto"`
means one engine's soft block no longer empties the whole search.

## The browser (desktop app)

In the desktop app, Coscribe has its own browser: the **Browser panel**
(the globe button) holds real tabs, and the AI uses those same tabs
through the `browser_*` tools -- `browser_navigate`, `browser_snapshot`,
`browser_click`, `browser_type`, `browser_press_key`,
`browser_select_option`, `browser_hover`, `browser_scroll`,
`browser_wait_for`, `browser_navigate_back`, `browser_tabs`, and for
what a page throws up along the way `browser_handle_dialog`,
`browser_file_upload` and `browser_evaluate`. The panel
opens by itself when the AI starts, every step happens in front of you (a
blue frame marks the page it's working in, a dot where it clicks, and a
"Coscribe is using the browser · Stop" bar), and you can take over at any
moment -- sign in, solve a CAPTCHA, or point at something: **Select
element** sends one element (a crop plus its text); the **pen** freezes
the page into a screenshot you can mark up -- pen, line, arrow,
rectangle, ellipse or text, in red, blue, green, black or white, with
undo/redo -- and "Add to chat" sends it with the page's title and URL and
any words you wrote on it.

- The AI reads a page as a list of its headings, text, links, buttons and
  fields, each actionable one with a ref (`[ref=e12]`), and acts on refs.
  Clicks and typing are sent as real input events, so sites treat them
  like yours.
- Instead of a ref, an action also takes the element the way the snapshot
  prints it -- `checkbox "All items"`, `textbox "Posting date" #2` for
  the second field of that name -- and waits for it to appear: 30s by
  default, or whatever the step's `timeout` says (up to an hour), so a
  workflow run on a slow network can be given more room in the step
  editor.
  Refs are numbered afresh on every page load, so saved workflows name
  elements this way: drafting a workflow from a conversation rewrites
  each ref into its element's description, and a draft still holding a
  bare ref is sent back to the curator.
- Every step waits for what it set off: a page load, and any request the
  page made since the step began (500ms quiet, at most 8s -- a floor so
  steps don't rush, not a limit: reaching it isn't an error), so pages
  that swap in content by script -- SAP WebGUI, most web apps -- are
  ready for the next step. Anything slower is waited for explicitly:
  `browser_wait_for` waits for text to appear or go away ("Generating
  export…"), for an element, or for a download to finish, with a
  `timeout` of up to an hour. Keys include F1–F12 and combinations like
  `Shift+F4`.
- **Downloads** started by the AI's steps are saved without the save
  dialog (which would stall an unattended run) to `downloads/` in the
  conversation's workspace -- a scheduled task's own workspace for its
  runs -- where the AI's file tools can read them and runs don't mix;
  a taken name gets " (1)". The step reports a quick download as
  finished, and a slow one as started, for `browser_wait_for(download=True)`
  to wait out; either way the wait takes it, and with `save_to` moves it
  into a folder the conversation can write to, under the site's own file
  name (" (1)" if taken). A workflow drafted from a conversation that
  downloaded something gets a "folder to keep it in" input for this --
  the user's folder if the conversation named one, else `downloads` --
  and in chat the AI asks where to keep downloads before drafting. Your
  own downloads still ask where to save.
- **Stop** also reaches the desktop app: the step in progress there (a
  wait can run for an hour) ends at once, and steps that conversation
  had queued are dropped.
- **Iframes**, including ones from other sites (payment widgets, embedded
  forms), show indented under their `iframe` line with refs like
  `[ref=f1e3]` that click and type the same way. To keep embedded pages
  from crowding out the page itself: frames smaller than 80×40 or hidden
  are left out, each frame shows at most 80 lines / 5000 characters (the
  note says which address to open for the rest), and frames nest at most
  two deep.
- **Dialogs**: when a page opens an alert or confirm, the step's result
  says so and the AI answers it with `browser_handle_dialog` (OK or
  Cancel); nothing else runs on that page until it's answered, by the AI
  or by you in the dialog box itself. `prompt()` never appears: Electron
  doesn't support it and answers it as cancelled.
- **Uploads**: `browser_file_upload` puts files from the conversation's
  folders into a file field, or into the upload button most sites put in
  front of a hidden one -- the system file dialog is caught and answered
  instead of popping up. Paths outside the folders the conversation can
  read are refused.
- **`browser_evaluate`** runs a JavaScript expression in the page, for
  what a snapshot doesn't show; it needs approval like running a script.
- Sign-ins persist in the browser's own profile, separate from your
  everyday browser (⋮ → "Clear browsing data…" clears it; ⋮ → "Save
  screenshot…" saves the page as a PNG). Sites get no
  camera, microphone, location or notification permission.
- **Site permission**: the first time the AI's browser tools touch a
  site in a conversation, the Browser panel asks -- Don't allow, Allow
  for this chat, or Always allow. ⋮ → "Manage allowed sites…" lists the
  always-allowed ones (add, remove, clear all); pre-allowing a site is
  how an unattended scheduled task gets through without a prompt (an
  unanswered prompt counts as no after three minutes). Kept by the
  desktop app in `browser-settings.json` in its user-data folder.
- Up to 9 tabs, as in Claude's browser: past that "+" is disabled, a link
  that would open a new tab loads in the current one, and the AI is told
  to close or reuse a tab.
- **Links** in chat messages open in a Browser panel tab (⋮ → "Open links
  in built-in browser" switches to your own browser); the app window
  never navigates away.
- Beyond the site prompt, reading a page needs no approval; clicking,
  typing, pressing keys, choosing options, answering dialogs and
  uploading are gated like other actions with outside effects (automatic in Auto mode unless the reviewer
  objects). The AI is told
  never to type passwords or payment details and to ask before anything
  that sends, buys, posts or deletes.
- Only http/https pages: the AI can't open `file://` pages to get around
  the folders a conversation has.
- No cookie import from your everyday browser: Chrome and Edge encrypt
  their cookies with an app-bound key other programs can't use, so only
  Firefox could be read, and bringing live sign-ins into a browser an AI
  drives isn't worth that narrow gain. Sign in once in the Browser panel
  instead; it stays signed in.
- This replaces the Playwright connector, which is no longer in the
  connector catalog: it drove a separate browser window with none of the
  panel's sign-ins, and returned a full page snapshot after every action.
  If you still have one configured, the AI is told not to use it for
  pages in Coscribe's browser.
- How it's wired: the desktop app starts the server with a random token,
  connects to `/internal/browser-host` with it and carries out each
  command on its tabs (`office-agent-desktop/src/main/browserAgent.ts`);
  no remote-debugging port is opened. Pages, frames, dialogs and input go
  through the DevTools protocol in-process (`webContents.debugger`,
  `browserCdp.ts`), attached to a tab on the AI's first step there -- a
  tab you only browse stays a plain one. The new tools are loaded on
  demand like other less-used tools, so a conversation that never meets a
  dialog or an upload doesn't carry them. Outside the desktop app the tools
  aren't offered, and the Browser panel falls back to a screencast of a
  headless browser.

## Skills

Every skill is a folder with a `SKILL.md` (YAML frontmatter
`name`+`description`, then markdown instructions), optionally with
reference files and scripts beside it -- the same format [Claude Code's
Skills](https://code.claude.com/docs/en/skills) use. Settings → Skills
lists them in three groups:

- **Built into Coscribe**: *PPTX Pages*, *PPTX Slides*, *Excel
  Spreadsheets*, *Word Documents* and *Skill Creator*. They can be switched off but not
  removed.
- **From Anthropic** (the **Discover** tab): Apache-2.0 skills from
  [anthropics/skills](https://github.com/anthropics/skills) that work with
  Coscribe's own tools -- algorithmic-art, brand-guidelines,
  canvas-design, claude-api, frontend-design, internal-comms, mcp-builder,
  theme-factory. Nothing is bundled: **Add** downloads that one skill's
  files, pinned to one upstream commit, and checks each against a SHA-256
  in `src/coscribe/skill_catalog.json` before it lands (regenerate the
  catalog with `scripts/build_skill_catalog.py <clone>`). Anthropic's
  docx/pdf/pptx/xlsx skills aren't offered: their license forbids
  redistribution, and Coscribe's built-in skills cover those formats.
  A removed skill shows up in Discover again.
- **Created by you**: folders in `COSCRIBE_SKILLS_DIR` (default
  `./skills`), whether dropped in by hand, uploaded (Add → Upload a
  skill, `.zip`/`.skill`/`.md`) or written with Add → Create with
  coscribe.

Clicking a skill opens it: **Overview** (description, the Coscribe tools
it mentions) and **Contents** (its file tree; Markdown renders with a
preview/source toggle, other text files show with line numbers). The ⋮
menu turns a skill off or removes it.

**On/off is global**: a switched-off skill isn't offered in any
conversation, and the change applies from the next message, including in
conversations already open. Every skill is on until switched off; the
off-set lives in `<COSCRIBE_STATE_DIR>/skills.json`. Being on only means a
skill is *offered*: the Coordinator still decides for itself whether a
turn calls `load_skill(name)`. A skill never narrows the *tool* set.

Every enabled skill's name and description are always visible to the
Coordinator (so it knows what's on offer and when to reach for one); the
full body is loaded on demand via `load_skill(name)`, and
`read_skill_file(name, path)` reads any bundled reference/asset file the
instructions point to. Both are low risk, no approval needed — same tier as
`read_file`. Whether to actually call `load_skill` (and, later,
`review_work`) is left to the model's judgment, the same "instructed, not
enforced" philosophy the [Subagent delegation and
review](#subagent-delegation-and-review) section below explains for
`review_work` itself — a skill toggle widens what's on offer, it doesn't
force a review step.

## Memory

The file at `COSCRIBE_MEMORY_PATH` (default `./MEMORY.md`, auto-created,
gitignored by default -- track it yourself if you want shared/team memory) holds
your global instructions: Settings › General › Global instructions edits it, and whatever
is in it is sent to the model in every conversation. Only you write to it: the
model has no tool for it. It is meant to stay a short, curated list (a
preference, a stable detail) -- not a running log, and not addressed by
`/compact` (which only
ever touches a single thread's conversation history, a much faster-growing
and more urgent problem than a short memory file).

## Subagent delegation and review

The Coordinator can hand a self-contained task to a sub-agent
(`runtime_lg/subagents.py`'s `build_delegation_tools`):

- `spawn_agent(description, prompt, instructions="", model="", tool_names="")`
  waits for the sub-agent's report; `spawn_agent_background(...)` returns a
  `task_id` at once. Only the report re-enters the conversation.
- **A background sub-agent reports back by itself**: when it succeeds,
  fails, or you stop it from the panel, its report (or error) arrives in
  the conversation as a message of its own -- drawn as a "Sub-agent
  finished / failed / stopped" card -- and starts a
  turn right away, or right after the turn in progress. No polling, and no
  wake to set up. With nobody typing, a chain of these turns (a report,
  another sub-agent, its report...) is asked to wind down on the third and
  stops starting turns after the fifth, until the user speaks.
  `check_subagent_task` shows one still running; `stop_subagent` stops one.
- **A step budget**: a sub-agent runs under Settings → General → Max
  turns and is told so, with an instruction to keep the work in
  proportion to the task. One that uses every step is asked for its
  report from what it actually did, rather than ending on the cap's bare
  "Model call limits exceeded".
- **A hung model call fails the run**: 180 seconds without a single
  streamed token from the model ends a sub-agent with that error (tool
  calls aren't timed -- a slow tool isn't a hung one).
- **Model**: any configured model (`provider:model`); empty means the
  conversation's own. When more than one is configured, the Coordinator asks
  the user which to use the first time it delegates.
- **Tools and folders**: by default the sub-agent gets the Coordinator's own
  tools (found through `search_tools` when tool deferral is on), bound to the
  conversation's folders; `tool_names` narrows that to a list. Tools bound
  to the parent's own conversation stay with the parent: the sub-agent
  list/check/stop tools (a sub-agent listing them finds itself "running"
  and takes its task as someone else's), wakes, and the to-do list.
- **Approvals** go through the conversation's own policy -- plan mode,
  Accept Edits, exec policy and hooks apply as they do to the Coordinator;
  Auto mode's reviewer also sees the task the sub-agent was handed, so "use
  a sub-agent, don't do it yourself" doesn't read as a ban on the
  sub-agent doing it --
  and a call that needs the user is answered in the **Sub Agents** panel,
  which opens by itself to it. A background sub-agent can ask after the
  parent's turn has ended, or with no tab open; it waits until answered.
- **Sub Agents panel** (the header's branch icon; it and the Browser panel
  share the right side, one at a time): running sub-agents as
  cards with elapsed time, model, tokens, tool uses, what each is doing and
  a Stop button; finished ones folded under "Finished N" with a clear
  button. Opening one shows its model, the prompt it was given, and its
  transcript drawn like the chat. Stop on the parent's turn also stops the
  sub-agents it's waiting for; background ones keep going.
- A sub-agent's transcript lives in memory, so a server restart loses it
  (its record and report stay).
- `review_work(original_request, summary_of_work, file_path="", preview_name="")`
  -- runs a fixed Reviewer persona (a fresh agent that didn't do the work)
  to check a result against what was actually asked, before the Coordinator
  finalizes or acts on it. Unlike `spawn_agent`, the Reviewer isn't given a
  free tool whitelist -- it always gets the same fixed, read-only toolset
  (`read_docx`/`read_pdf`/`search_pdf`/`read_xlsx`/`read_pptx` today, every
  tool with `category="documents"` and no approval requirement), so passing
  `file_path` lets it independently read the actual file rather than just
  trusting the Coordinator's own summary. Passing `preview_name` (a write
  tool's own `preview_path`, when it returned one) goes further: the
  Reviewer is shown the actual rendered image, not a description of it --
  real vision, not just text. This is genuinely useful, not just plumbing:
  live-tested against a real full-bleed background-image slide, it
  independently named the exact legibility problem, suggested the right
  fix (a semi-transparent overlay), and separately caught a stray bullet
  point and an alignment inconsistency nobody had pointed out to it.
  **Cross-provider verification** (a follow-up pass to the initial
  Gemini-only test above): `review_work`'s image content block is the
  standard LangChain OpenAI-style shape (`{"type": "image_url",
  "image_url": {"url": "data:image/png;base64,..."}}`). Reading the
  installed `langchain-anthropic`/`langchain-google-genai`/
  `langchain-openai` source confirms all three convert it correctly into
  each provider's native multimodal format (`langchain_anthropic`'s
  `_format_image()` regex-matches this exact data-URI shape and converts
  it to Anthropic's native `base64` block). Live-verified for two of the
  three wired code paths: Gemini (above), and the `ChatOpenAI` class
  shared by both the native `openai:` provider and any custom
  OpenAI-compatible provider (tested against a real vision model on a
  configured custom provider -- the model correctly engaged with the
  image's content, not just echoed text). The native Anthropic path has
  no live Anthropic API key available in this environment, but got an
  indirect check: routing `ChatAnthropic` at DeepSeek's
  Claude-SDK-compatible endpoint (same `ChatAnthropic` class, same
  `_format_image` conversion code, different `base_url`) confirmed the
  image block reaches the model layer intact -- it correctly answered
  "yes" to "is an image attached" only when one actually was sent -- but
  the described content was fabricated, consistent with the model behind
  that endpoint not having real vision capability rather than a
  conversion bug. Net: the format-conversion code itself is verified
  correct; whether a genuinely vision-capable Claude model gives
  `review_work` useful judgment on a real screenshot is still unconfirmed,
  for lack of a real Anthropic API key to test against.

`ARCHITECTURE.md` describes "Specialist agents" as domain-divided experts
with tool sets decided by configured MCP/Skills -- in practice that's not a
fixed roster of named agent types, it's `spawn_agent` used ad hoc with
whatever instructions and tool subset fit the sub-task at hand. The Reviewer
is the one genuinely new, dedicated agent role.

A sub-agent can never be given `spawn_agent`, `review_work`,
`ask_user_question`, `create_scheduled_task` or `draft_workflow`, so
delegation can't recurse and questions stay with the user's own
conversation.

## The code module (optional)

A coding agent, [Codex](https://github.com/openai/codex) (Apache-2.0), as
Coscribe's second agent. It writes and runs code in your folder: scripts
that process your files, tools you'll reuse, fixes for a script that fails.
It's an assistant to the chat, not a mode of its own: you talk to the chat,
and the chat hands over what needs real code.

- **From a chat**: with *Chats can hand tasks to Code* on (Settings › Capabilities,
  or `COSCRIBE_CODE_MODULE_ENABLED=true`), a chat can hand a programming
  task to it through `run_code_task`; the run shows in the Sub Agents panel,
  where you watch, approve and stop it.
- **Follow-ups**: when you ask for changes to what a code task made, the
  chat carries on from that task (`continue_task`): Codex resumes the same
  thread, so it remembers what it did and sees its own files, and the chat
  only says what to change. The follow-up is a task of its own in the Sub
  Agents panel, listed next to the one it continues. If Codex no longer has
  the thread, it is given the earlier task and its report instead.
- **Models**: Codex only speaks OpenAI's Responses API -- OpenAI, or a
  custom provider that serves `/responses` (DeepSeek does). It runs on *Model
  for code* (`COSCRIBE_CODE_MODEL`), or the chat's own model when that's
  unset; when the chat uses a model Codex can't (Claude, Gemini), the chat
  is told to ask you to pick one in Settings › Capabilities.
- **Download**: nothing is bundled with the app. The pinned Codex build
  (~111 MB download, ~330 MB on disk on Windows) is fetched into the state
  directory the first time it's used, or from Settings › Capabilities, which can
  also remove it; the download is checked against pinned hashes.
- **Approvals**: a file change comes to you as an approval under the permission mode; *Approve*
  answers one card, *Allow for this task* that kind of change for the rest of the task, and
  *Change files without asking* in Settings › Capabilities allows it for good (Plan mode still
  declines). Commands run only where the command sandbox is set up (Settings › Capabilities,
  decision 0022), under a profile that holds them to the folder; elsewhere a command is refused
  without a card, except a plain read of the folder (`ls`, `cat`, `grep`, ... or on Windows
  `Get-ChildItem`, `Get-Content`, `Select-String`, ... with nothing that writes, chains or leaves
  the folder; Coscribe decides this itself, not Codex). Stop ends the commands it started.

Not there yet: a run on real Windows.

## MCP servers

Set `COSCRIBE_MCP_CONFIG_PATH` in `.env` to a JSON file in the same
`mcpServers` shape as Claude Desktop's config to give the Coordinator tools
from external MCP servers (document processing, browser automation, etc. —
see `../ARCHITECTURE.md`):

```json
{
  "mcpServers": {
    "custom-db": {
      "command": "npx",
      "args": ["my-mcp-server"],
      "env": { "API_KEY": "..." }
    }
  }
}
```

Same schema Claude Desktop, Claude Code, and Cursor all use for local
(stdio) MCP servers -- `command`/`args`/`env` per server, keyed by name --
since it's the shape Anthropic's own MCP spec examples popularized, not
something Coscribe invented. A remote server is an entry with a
`server_url` (and optional `headers`) instead.

**Settings → Connectors** lists the catalog and your own connectors
(Type Local or Web, "Custom" for ones you added; Status a check when
connected, Connect for a catalog one not added yet). **Add → Add custom
connector** takes a name and an MCP server URL, or -- "Run a local command
instead" -- a command, arguments and environment variables (one
`KEY=value` per line). `env` and header values are never echoed back to
the browser after saving, only masked.

Click a connector for its page. A catalog one not added yet shows what it
is, who makes it and its package, with **Connect**. An added one has
**Disconnect**, a ⋮ menu (Reconnect; Check for updates when its args pin a
`package@version` -- it looks the version up on npm and updates that one
arg in place), and **Tool permissions**: its tools in "Read-only tools" and
"Write/delete tools" (the server's own `readOnlyHint`; a tool without one
counts as write/delete), each set to **Always allow** (runs without asking,
not even Auto mode's reviewer), **Needs approval** (the default: the
conversation's mode decides, as for `write_file`) or **Blocked** (the
model never sees it). A group's menu sets all its tools at once. Kept in
`connector_permissions.json` in the state folder, not in `mcp.json`, and
applied to open conversations at once.

Tool names are always prefixed with the server name to avoid colliding with
the built-in file tools. A server that fails to connect at startup (or the
config file itself being missing) is skipped with a warning rather than
blocking the others or crashing the process. Adding, removing, updating or
changing permissions takes effect right away, open conversations included;
the `coscribe` CLI reads MCP config once per invocation and doesn't apply
the permissions.

Catalog entries pin an exact package version rather than `@latest` --
an unpinned tag makes `npx` hit the npm registry on every startup just
to check for a newer version.

The built-in catalog no longer includes `git`/`github` entries (and the
GitHub OAuth Device Flow sign-in button that used to come with the
`github` one) -- Coscribe is a general file/task automation assistant,
not a developer coding tool, so a git/GitHub connector isn't relevant to
its target audience by default. Either is still addable by hand as a
custom connector for anyone who specifically wants one.

`tools/mcp.py` also monkeypatches a real bug in aisuite 0.1.14 (the latest
published release) on import: `MCPToolWrapper._create_signature` builds a
Python function signature straight from an MCP tool's JSON Schema property
order, which breaks (`ValueError: non-default argument follows default
argument`) the moment an optional property is listed before a required one
-- valid JSON Schema, and exactly what most of the official playwright-mcp
server's interaction tools (`browser_click`, `browser_type`, `browser_hover`,
...) do. The patch only reorders parameters (required first) before handing
them to `inspect.Signature`; no semantic change, since tool calls are always
keyword-based. Verified live: without the patch, `connect_mcp_tools` against
a real playwright-mcp server returns zero tools; with it, all 24 connect and
the Coordinator can drive real tool calls through them.

The web UI's **+** → **Add connectors** panel edits this same file for
you (see the Web UI section) instead of you writing this JSON by hand —
functionally identical either way.

## Custom LLM providers

Beyond the built-in `anthropic:`/`openai:`/`gemini:` prefixes, any
OpenAI-compatible API can be registered as its own model prefix by setting
`COSCRIBE_PROVIDERS_CONFIG_PATH` in `.env` to a JSON file:

```json
{
  "providers": {
    "deepseek": { "base_url": "https://api.deepseek.com/v1", "api_key": "sk-..." }
  }
}
```

Once registered, use it like any other model, e.g.
`COSCRIBE_DEFAULT_MODEL=deepseek:<a real current model id from DeepSeek's
own docs>` -- deliberately not a specific example model id here: a
vendor's own model lineup is outside this project's control and turns
over on its own schedule, so a hardcoded example goes stale (a real,
live-hit case: this doc used to say `deepseek-v4-flash`, which was
already wrong by the time a user tried it -- see
`runtime_lg/README.md`'s matching note). No provider-specific code is
needed: `resolve_chat_model` (`runtime_lg/providers.py`) hands the
`base_url`/`api_key` straight to `langchain_openai.ChatOpenAI`'s
constructor -- that's all an OpenAI-compatible endpoint needs.
`default_model` in the file is just a UI convenience for pre-filling the
"add custom provider" form (left blank for third-party vendors in the
catalog itself, for the same staleness reason -- fill in your own
current model id there); it isn't read by anything else.

The web UI's **Settings → Providers** tab (see the Web UI section) edits
this same file for you, with DeepSeek, Kimi (Moonshot), Zhipu GLM, and a
local Ollama runtime as one-click catalog entries plus a form for any
other OpenAI-compatible API -- those four are convenient examples, not
an exhaustive list; none of them pre-fill a guessed "default model" (see
above) since that goes stale, fill in your own. Adding or removing a
provider here is saved immediately, no restart needed, and takes effect
in already-open conversations too, not just new ones. Anthropic,
OpenAI, and Gemini (the three built-in providers, configured by API key
rather than base URL) also appear in this tab once their key is set in
**Settings → API Keys**, alongside an optional "default model" field per
key -- that pairing is what lets the composer's model pill (below) offer a
one-click switch to that provider without you having to remember or type
its exact model id.

## Secrets storage

Every secret Coscribe itself writes -- built-in provider API keys (`.env`),
custom providers' `api_key` (`providers.json`, above), and MCP server
`env`/header values including a connected GitHub token (`mcp.json`, see
[MCP servers](#mcp-servers)) -- goes through the same two-layer hardening:

1. The file itself is always written with owner-only permissions (`0o600`),
   regardless of the layer below.
2. If a working OS keychain is available (macOS Keychain, Windows
   Credential Locker, or a Linux Secret Service/kwallet daemon, via the
   `keyring` package), the actual secret *value* lives there instead --
   the file on disk holds only a small reference, not the real key.
   If no keychain backend is available (common on a headless Linux
   server/container -- no Secret Service running), storage falls back to
   the permission-hardened plaintext file above; nothing fails, saving a
   key/token always works either way.

This degrades the same way the office-program features do elsewhere in
this project: best effort, never the reason an operation fails. One real
tradeoff worth knowing: a keychain-backed secret doesn't travel with a
copied `.env`/`state_dir` the way a plaintext one does -- if you move
Coscribe's config to a different machine (or the keychain becomes
unavailable for any other reason) and it can't read a secret back, it
tells you plainly rather than silently breaking; just re-enter that key/
token via Settings.

## Hooks

Set `COSCRIBE_HOOKS_CONFIG_PATH` in `.env` to a JSON file listing shell
commands per lifecycle event:

```json
{
  "PreToolUse": ["./hooks/audit.sh"],
  "PostToolUse": ["./hooks/log.sh"],
  "SessionStart": ["./hooks/notify.sh"]
}
```

Each command receives a JSON payload on stdin describing the event
(`event`, `tool_name`, `arguments`, `agent_name`, plus `result` for
PostToolUse or `thread_id` for SessionStart) and is interpreted by its exit
code:

- **PreToolUse** runs before *every* tool call, regardless of risk level or
  Plan Mode/Accept Edits Mode — it's a governance/audit layer independent of
  the built-in risk classification. A nonzero exit denies the call outright
  (no approval prompt reached); stderr becomes the reason shown to the model,
  the same way a user-denied or Plan-Mode-denied call already surfaces.
- **PostToolUse** runs after a tool call succeeds, for logging or side
  effects. It can't undo the action; a failing hook is only logged as a
  warning.
- **SessionStart** runs once when the CLI starts. A failing hook is logged
  as a warning rather than blocking startup, same tolerance as a broken MCP
  server or malformed skill.

Hooks run arbitrary shell commands with your own permissions — only point
this at configuration you trust, same trust model as an MCP server's
`command`/`args`.

## Web UI

The frontend is a React + TypeScript app in `frontend/` (a sibling
Node/TS project, not part of this Python package) -- see
`frontend/README.md` for its dev loop, architecture, and live-verified
feature-parity notes. `npm run build` there compiles straight into
`src/coscribe/web/static/`, which is what `coscribe-web` below
actually serves; that directory is a build artifact (gitignored), not
hand-edited source.

If [Setup](#setup) above already included the `web` extra and the
`npm run build` step, just run:

```bash
coscribe-web          # binds 127.0.0.1:8000 by default
```

If `coscribe-web` isn't on `PATH` (e.g. right after installing, or in some
Windows shells), `python -m coscribe.web.app` runs the identical entry
point without depending on `PATH` at all.

A local, single-user web UI covering the same ground as the CLI: a chat
pane, an approval prompt for anything requiring approval, and a live task
panel -- the three pieces `../ARCHITECTURE.md` calls out as the core UI.
Hooks configuration stays file-based, same as the CLI; MCP and Skills now
have a friendlier path too (see below), but hand-editing their config
files still works exactly as before.

`coscribe-web [--host HOST] [--port PORT]` starts a FastAPI process
that serves the frontend and a `/ws/<thread-id>` WebSocket per
conversation; opening `/` generates a thread id and puts it in the URL
(`?thread=...`), so reloading or revisiting that URL resumes the same
thread, same as `coscribe --thread <id>`. The mode pill (bottom-left of
the message box) covers Manual/Accept Edits/Plan/Auto -- it just sends the
same `/accept-edits`/`/plan`/`/auto` text the CLI understands, no separate
protocol.

The server answers only requests whose `Host` is `localhost`, `127.0.0.1` or `::1` and, when a
browser sends an `Origin`, only that same set (a page on another site, or a rebound hostname,
is refused with 403 and a WebSocket is closed). To serve it under another name, for example with
`--host 0.0.0.0` or behind a reverse proxy, list the names in `COSCRIBE_ALLOWED_HOSTS`
(comma-separated, host names without ports): `COSCRIBE_ALLOWED_HOSTS=coscribe.lan coscribe-web --host 0.0.0.0`.
`--host <name>` for a specific name adds that name by itself.
The web layer (`src/coscribe/web/app.py` + `conversation/session.py`) runs
directly on runtime_lg -- `ChatSessionLG` compiles and drives a LangGraph
agent per thread, it isn't a bridge in front of a separate execution
engine.

**Task details panel** (right side, toggled by the panel icon at the top
right; remembered per browser, shown on windows at least 1024px wide once
a conversation has started) -- three collapsible sections, all derived
from the thread's own checkpointed messages via
`GET /api/threads/{id}/activity`, so they cover runs nobody watched and
refresh live as each tool call finishes:

- **Progress** -- the model's plan (`task_create`/`task_update`) as a step
  row and a checklist.
- **Outputs** -- every file the conversation created or changed: the
  `path` of any successful `WRITE_LOCAL`/`EXTERNAL` tool call, plus the
  workspace files a script reports writing (see [Running
  scripts](#running-scripts)), newest first. Clicking one opens it with
  the OS's default app (`POST /api/threads/{id}/files/open`) -- only for
  document/media types, so a script or executable a run wrote is never one
  click from running; those can still be shown in their folder or
  downloaded (`GET /api/threads/{id}/files/download`). Paths resolve
  through the thread's own workspace scope, same as the tools.
- **Context** -- files it read, skills it loaded, MCP connectors and
  built-in tools it used (with counts).

On a scheduled run the panel's header names the task (click for its page)
and shows that run's status. The Browser and Sub Agents panels use the
same space, so opening either one hides this panel until it's toggled back.

Below the message box, a small bar shows how much of the model's context
window the current thread is using (updates after each reply) next to the
active model's name, shown as a pill (bottom-right of the message box).
The token count comes from the real model response's own `usage_metadata`
-- specifically, the *last* model response within a turn (a tool-calling
turn involves two or more separate responses; only the final one's own
total reflects the whole conversation's current size, since each
response's `input_tokens` already includes everything sent before it --
summing multiple responses together would double-count). Omitted entirely
(no event, bar stays in its default state) if the active model never
reports usage at all, rather than showing a fabricated number. The
max-size half of that bar resolves via `LLMClient.get_context_window` --
a real, live number from the provider when it offers one (currently just
Gemini, via `GeminiProvider.get_context_window`'s `client.models.get()`
call -- not a hardcoded guess), falling back to a rough, explicitly
unverified per-vendor estimate otherwise. Clicking the model pill opens a picker
listing every provider with a key/default model configured (built-in and
custom, from **Settings → Providers**/**API Keys**) plus a free-text
field for any other "provider:model" string -- picking one switches
*this thread's* model immediately, no restart, no reconnect. The switch
is per-thread and in-memory, same as the mode pill's Plan/Accept-Edits
toggle: it survives a page reload (restored from the session's live
state) but not a process restart, which resets every thread back to
`COSCRIBE_DEFAULT_MODEL`.

The **+** button next to the message box opens three things:

- **Slash commands** -- the same autocomplete list that also pops up
  automatically while typing `/` in the message box (fixed commands plus
  every loaded skill); typing a skill's name as `/<skill-name>` works
  exactly as it does in the CLI.
- **Add files or photos** -- images are attached as real multimodal image
  parts the model actually sees (not just a filename reference) -- see
  `ChatSessionLG.handle_user_message`'s `images` parameter. Anything else
  (a `.docx`, a `.pdf`, a plain text file, ...) is uploaded straight into
  the workspace via `POST /api/upload` (capped at 25MB, name collisions
  auto-renamed rather than overwritten) and referenced by path in your
  message, so the Coordinator reaches for `read_docx`/`read_pdf`/
  `read_file` on it like any other workspace file -- both kinds show up
  as removable chips above the message box while queued.
- **Add connectors** -- a small curated catalog (`office365`; Slack is
  set up by hand in the Custom tab; reading a web page is the built-in
  `read_web_page` tool and using websites is the desktop app's own
  browser, so neither needs a connector) plus a form for any custom MCP server, backed by
  `GET`/`POST /api/mcp/servers` and `DELETE /api/mcp/servers/{name}` in
  `web/app.py`. These are the same stdio MCP servers the CLI's
  `COSCRIBE_MCP_CONFIG_PATH` config file already supports (see below) --
  the panel just reads and writes that file instead of you hand-editing
  JSON, defaulting to `./mcp.json` if you haven't set one. Same
  restart-required caveat as the settings panel: MCP connections are only
  ever made once at process startup.
- **Providers settings tab** -- register any OpenAI-compatible API
  (DeepSeek, Kimi, GLM catalog one-click entries, or a custom form for any
  other) as a new model prefix, backed by `GET`/`POST /api/providers` and
  `DELETE /api/providers/{name}` in `web/app.py`. Reads and writes the same
  `providers.json` file the `COSCRIBE_PROVIDERS_CONFIG_PATH` setting
  points at (see [Custom LLM providers](#custom-llm-providers) above). API
  keys are masked in the configured list, same as the API Keys tab.
- **Appearance** (top of Settings → General) -- Theme (match the system,
  light or dark), Interface font for the whole interface (Figtree, the
  default; the system's own UI font; or OpenDyslexic -- Figtree and
  OpenDyslexic bundled under the OFL) and Motion (follow
  the system, or reduced). Applied the moment you pick it, and saved as
  `COSCRIBE_THEME`, `COSCRIBE_INTERFACE_FONT`, `COSCRIBE_MOTION` in `.env` --
  the desktop app serves the page from a new port each launch, so browser
  storage wouldn't keep it. Claude's own Anthropic Serif isn't offered: it
  is Anthropic's proprietary typeface and can't be redistributed.
- **Tools settings tab** -- a read-only list of the built-in tools the
  Coordinator always has access to (file/document/spreadsheet/task/
  memory/subagent, plus Skill-loading tools if any Skills are configured),
  in collapsible categories (collapsed at first, each with its tool
  count), each tool with the first sentence of its description and a
  "requires approval" badge for medium-risk
  tools. Backed by `GET /api/tools`, which builds a real Coordinator agent
  (the same entrypoint `cli.py`/the WebSocket session use) and reads off its
  tool list, so it can never drift out of sync with what the agent actually
  has. Distinct from Connectors (external, MCP) and Providers (which LLMs).

The gear icon opens a settings panel that reads and writes `.env` directly
(`GET`/`POST /api/config` in `web/app.py`, using `python-dotenv`'s
`dotenv_values`/`set_key` so unrelated lines and comments are left alone).
Provider API keys are only ever shown masked (last 4 characters) and a
blank field on save means "leave it unchanged," so the real value never
round-trips through the browser. Nothing hot-reloads -- `Settings` and the
provider clients are all built once at process startup -- so saving shows
a "restart required" notice rather than silently doing nothing; that
matches editing `.env` by hand today, it's just safer to do from the UI.
Proxy variables (`HTTPS_PROXY`/`HTTP_PROXY`/`NO_PROXY`) aren't in the
Settings panel, but `.env` works fine for them (see `.env.example`) --
`runtime/dotenv_file.py` loads it with `override=True`, so a `.env` value
win over a stale OS-level proxy already set, the same real corporate-
machine bug that fix was written for. Left out of the panel because a
masked/never-round-tripped text field would be a worse editing experience
for a plain URL than just opening `.env` directly, not because `.env`
doesn't work for it.

Binds to `127.0.0.1` by default; this is a local single-user tool, not
meant to be exposed beyond your own machine.

Replies stream token-by-token (both here and in the CLI) for every
provider uniformly -- anthropic/gemini/openai and any OpenAI-compatible
custom one -- via one shared LangGraph `agent.astream(..., stream_mode=
["messages"])` call (`conversation/session.py`'s `_stream_turn`), not
per-provider vendored code. This wasn't always true: an earlier runtime
had per-provider streaming code that only covered the vendored Gemini
provider, with Anthropic/OpenAI falling back to a single non-streamed
chunk -- see `runtime_lg/README.md` for the full history of the
migration that replaced that runtime with the current one.

## Desktop app

`../office-agent-desktop/` is an Electron shell around this same web UI
-- not a second interface to maintain. It starts `coscribe-web` as a
supervised local subprocess ("sidecar") on a free port and opens a
window pointed directly at it -- see `office-agent-desktop/src/main/
index.ts`'s own module docs for the design. Browser mode (`coscribe-web`
+ a normal browser tab) keeps working completely independently.

This replaced an earlier Tauri shell at the Browser panel native-window
migration's Phase 4 cutover (see `../docs/history/roadmap-through-2026-10-08.md`); that
shell has since been removed.

**Menu** (the ☰ button; shortcuts work without opening it), laid out
like Claude's desktop app:
- **File**: New Session (Ctrl+N), Open File… (the composer's attach
  picker), Open Folder… (Ctrl+Shift+O, adds a folder to the conversation),
  Settings… (Ctrl+,), Close Session (Ctrl+W, back to the new-session
  screen), Exit. The items are carried out by the page; the shell sends
  each as a page event with a user gesture, since Chromium only opens a
  file chooser in response to one.
- **Edit**: Undo, Redo, Cut, Copy, Paste, Delete, Select All, and **Find…**
  (Ctrl+F) / Find Next (F3) / Find Previous (Shift+F3).
- View, Go (Back / Forward), Help.

**Find in page** (Ctrl+F in the desktop app and in a browser tab alike)
opens a small bar under the conversation's header icons: matches in the
chat are highlighted in place with the CSS Custom Highlight API (the
chat's DOM isn't touched, and matches follow a reply as it streams), with
a count, Enter / Shift+Enter or the arrows to step, Escape to close. A
match split across two styles (half of it bold) isn't found.

Two things only matter for the desktop build, not the browser one:
- **`_exit_when_orphaned` (`web/app.py`)**: when the shell sets
  `COSCRIBE_EXIT_WITH_PARENT=1`/`COSCRIBE_PARENT_PID`, the sidecar
  watches that PID and self-exits if it dies abruptly -- defense-in-depth
  alongside the shell's own kill-on-quit. A no-op otherwise.
- **Per-user app-data paths**: `workspace_root`/`state_dir`/`skills_dir`/
  `memory_path` default to paths relative to the process's
  cwd (correct for a terminal-launched server, meaningless for a
  double-clicked app with no natural project directory) -- the desktop
  shell sets each as an explicit `COSCRIBE_*` env var pointed at a
  real per-user directory instead
  (`~/Library/Application Support/coscribe` on macOS,
  `%APPDATA%\coscribe` on Windows). `.env` loading
  (`cli.py`'s `_dotenv_path`) falls back to the same directory whenever no
  `./.env` already exists in cwd, so the Settings panel's "paste your API
  key" flow works identically in both modes.

Building/running the desktop app needs its own toolchain (Node only, no
Rust) and its own PyInstaller-frozen copy of `coscribe-web` (**onedir**,
never onefile -- see `coscribe/packaging/coscribe-server.spec`'s
own docstring for the measured startup-latency reason, directly
continuing this project's own import-time work above). See
`office-agent-desktop/`'s own docs for the exact build steps; the short
version is `office-agent-desktop/scripts/stage-sidecar.sh` (builds the
PyInstaller binary and stages it into `resources/sidecar/`) then
`npm start` / `npm run dist:portable` / `npm run dist:nsis` from
`office-agent-desktop/`.

## Test

```bash
pytest
ruff check src tests
mypy src
```

Running the full suite (including `tests/web/`) needs the `web`
extra installed too: `pip install -e ".[dev,web]"`.

Tests do not require an API key or network access — they exercise
configuration loading and tool wiring directly (including `cli.py` and the
web backend, via `typer.testing.CliRunner`/`fastapi.testclient.TestClient`
with a fake LLM client). The actual LLM round-trip needs a real key and is
not covered by automated tests; run it manually to verify end-to-end
behavior.

CI (`.github/workflows/office-agent-ci.yml`) runs all three on every push/PR
touching `coscribe/`.
