# Design note: the Plan panel and the live task card (#506, with #505) (2026-10-21)

Design before code, as #506 asks. Reference screenshots are the maintainer's, from Claude's own app;
the front end is meant to look the same as them. Status: **for the maintainer's decision**.

## 摘要（中文）
- Plan 是一个和 Browser、Background tasks 并列的**独立右侧面板**，入口是任务清单图标加 "Plan"。
- 对话里有两样东西：①模型调用 `exit_plan_mode` 时出现的 "Claude proposed a plan" 卡片
  （Reject / Revise… / Accept / Accept and auto mode，Open plan 打开面板）；②模型一建任务列表，
  从那时起到任务全部完成，这一段里的说明句子和命令行**全部被一张任务卡片取代**。
- 卡片和面板里的 TASKS 都只是模型自己维护的任务列表（`task_create` / `task_update`）的显示；
  出错、停止、计划有变，由模型更新列表，前端不做特殊的出错逻辑。
- 计划是 `.md` 文档：对话里展开是源码（"Proposing plan"），面板里是渲染后的版本，计划被改后用红绿差异显示。
- 不改 wire，不改任何工具的 schema（决定 0001）。先做 #505，再做 #506 的四个 PR。

## What the screenshots show
1. **Plan panel** (right side, like Browser): title "Plan", expand and close buttons; "TASKS" list with a
   tick and strike-through for done, a dashed circle for to-do, a spinner for the current one. Its tab
   icon is the checklist glyph with the word "Plan".
2. **"Claude proposed a plan" card** in the conversation: `Reject`, `Revise…`, `Accept`,
   `Accept and auto mode`, and an `Open plan` link. `Revise…` turns the card into a text box
   ("What should change? (optional)") with `Back` and `Revise`.
3. **The plan opened in the panel**: rendered markdown, with the line "Select any text to leave a
   comment for Claude"; selecting text shows an "Add a comment" box.
4. **Proposing plan** row in the transcript: opens to the plan's markdown source.
5. **A changed plan**: the model asks (`ask_user_question`), then edits the plan; the transcript shows
   "Updated plan-….md +10 −11" opening to a red/green diff, and a new proposal card under it.
6. **Progress card in the conversation**: a bordered list, filled tick (done), ellipsis (doing),
   dashed circle (to do).

## Decisions proposed

### Where the items come from
The task list the model keeps (`TaskToolkit`, `tools/bookkeeping/tasks.py`: `task_create`, `task_update`,
`task_list`; statuses `pending`, `in_progress`, `completed`). The browser already sees those calls and
their results in the transcript, and `TaskPanel` already reads the saved list through
`getThreadActivity`. No plan text parsing. With no task list there is no card and no TASKS list;
the plan text alone is still shown in the Plan panel.

### What triggers what
- **Plan mode** (`ModePill`) is unchanged: the model researches, then calls `exit_plan_mode(plan)`.
  That makes the proposal card and opens the Plan panel on the plan text.
- **A task list** is independent of plan mode: the first `task_create` in a turn starts the live card,
  in or out of plan mode.

### The live task card
- Sits in the transcript where the first `task_create` happened and updates in place.
- **From that call until the last task is `completed` (or the turn ends), the narration sentences and
  command rows of that stretch are not drawn**: the card replaces them. Ten sentences become two or
  three items.
- Opening an item shows the calls made while it was `in_progress`, as the rows from #505; calls made
  while no item was in progress go at the end of the card.
- Always drawn in the transcript, never inside the card: an approval waiting on the person (manual
  mode always asks), and a question from `ask_user_question`.
- Done: the card collapses to a one-line summary and stays in the transcript. The model's final
  message and the person's messages are shown as usual.
- Failure, a stop, a changed plan: the model updates the list (edit, add, change a status) and the
  card follows. The front end adds no error logic. On a stop, the in-progress item stops spinning
  and keeps its state.
- After a reload the card is rebuilt from the saved history the same way (the calls are in it).

### The Plan panel
A new panel beside Browser and Background tasks (`App.tsx` switch, `dock/`), opened from the card,
the `Open plan` link, or the header icon. Two parts: the plan (markdown, rendered) and TASKS (the same
component as the card). It can be enlarged. Narrow window: the panel takes the whole width, as the
other panels do, and the card is a single column.
**Open:** `TaskPanel`'s Progress section shows the same list; proposal is to keep `TaskPanel` for
Outputs and Context and have Progress open the Plan panel instead.

### The plan as a markdown document
Shown as `.md`: the transcript row "Proposing plan" opens to the source; the panel renders it. A
revised plan is diffed in the browser from the two versions of the text (no new event, no schema
change). `Reject` ends planning and tells the model the user rejected it; `Revise…` sends the typed
text back (today's `revise` choice). Comments on selected text are sent back inside the `Revise`
feedback as quoted text plus the comment, so `wire.py` does not change.
**Open:** whether the plan is also saved as a real `.md` file in the thread's workspace, as Claude Code
does (`plan-….md`). Not needed for any of the above; it would give the person a file to keep.

### Wire and invariants
No new event is needed for any of this, and no tool schema changes (decision 0001: the tool list is
fixed and provider-cached). If a missing event shows up, it is added to `conversation/wire.py` first,
`python scripts/gen_wire_ts.py` regenerated, and said here.

## Order and pull requests
- **#505 first** (it owns the rows in `ToolRuns.tsx` the card reuses; #506 says so too):
  - part 1, #508: arguments and results as `name: value` lines, a Raw fold, `lib/toolFields.ts`;
  - part 2: every command as a `$ command` box, the file tools as one line, a Playwright spec.
- **#506**, after this note is accepted, about 600 lines at most each:
  1. Plan panel, its entry, the shared task-list component, the live card with the stretch replaced;
  2. the new proposal card (four buttons, Reject, Revise box, Open plan);
  3. diff of a changed plan;
  4. comment on selected text.
  Each has reducer or lib unit tests and a Playwright spec against the stub model, with before and
  after screenshots.

## Not verified
- Nothing here is built. Whether `task_create` calls arrive early enough in a turn to draw the card
  before the first command is to be checked against the stub model in PR 1.
- Behaviour on Windows and in the desktop shell is not tested.

## Questions for the maintainer
1. Is replacing the stretch (narration and commands) by the card what is wanted, with approvals and
   questions still drawn?
2. Should Progress in `TaskPanel` hand over to the Plan panel?
3. Is a saved `plan-….md` file wanted, or only the in-app document?
