// Generated from src/coscribe/conversation/wire.py -- do not edit.
// Regenerate with `python scripts/gen_wire_ts.py` (from office-agent/).

/** The conversation's settings, sent on connect and after each change. */
export interface StateEvent {
  type: "state";
  plan_mode: boolean;
  accept_edits: boolean;
  /** A reviewer model decides risky calls instead of the user. */
  auto_mode: boolean;
  model: string;
  effort: "low" | "medium" | "high" | "extra" | "max" | "ultra";
  /**
   * The model's own level that `effort` runs as (`xhigh` for extra, for example);
   * None when the model takes no effort setting.
   */
  effort_runs_as: string | null;
  context_window: number;
  /**
   * Skills offered in this thread's instructions: the global on/off set, re-read at
   * the start of every turn.
   */
  enabled_skills: string[];
  /**
   * The thread's main folder; a thread with no folders falls back to the server's
   * default workspace.
   */
  workspace_root: string;
  /** Whether workspace_root is a folder this conversation chose, not the default. */
  workspace_explicit: boolean;
  /**
   * The folders this conversation works in, the main one first; empty while it uses
   * the default workspace.
   */
  folders: string[];
  /** The connected connectors' tool names. */
  connector_tools: string[];
  /**
   * Only on the state sent right after connecting: whether a turn is already running
   * on this thread (typically a scheduled run), so the page shows it as running.
   */
  turn_in_flight?: boolean;
}

export interface UserEntry {
  kind: "user";
  text: string;
  images?: string[];
}

/** A note the user added while a reply was being worked on. */
export interface SteerEntry {
  kind: "steer";
  text: string;
  images?: string[];
}

export interface AgentEntry {
  kind: "agent";
  text: string;
}

export interface ToolEntry {
  kind: "tool";
  tool_name: string;
  arguments: Record<string, unknown>;
  result: unknown;
  /** True iff the tool's Python body raised (the checkpointed ToolMessage's status). */
  is_error: boolean;
}

export type HistoryEntry =
  | UserEntry
  | SteerEntry
  | AgentEntry
  | ToolEntry;

/** The thread's checkpointed messages, replayed once after connecting. */
export interface HistoryEvent {
  type: "history";
  entries: (UserEntry | SteerEntry | AgentEntry | ToolEntry)[];
  /**
   * Whether the checkpoint starts with a compaction note, i.e. whether
   * load_older_messages has anything to find.
   */
  has_older: boolean;
}

/**
 * Answer to load_older_messages: one whole pre-/compact epoch. `has_more` is a "try again"
 * hint, true whenever this call found a batch; an empty `entries` is the one unambiguous
 * "nothing earlier".
 */
export interface OlderMessagesEvent {
  type: "older_messages";
  entries: (UserEntry | SteerEntry | AgentEntry | ToolEntry)[];
  has_more: boolean;
}

export interface AgentDeltaEvent {
  type: "agent_delta";
  text: string;
}

/**
 * A call about to run; its tool_result follows. Not sent for a call waiting on approval
 * (approval_required shows that one).
 */
export interface ToolStartedEvent {
  type: "tool_started";
  tool_name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResultEvent {
  type: "tool_result";
  tool_name: string;
  /** The call's own arguments, taken from the preceding AIMessage's tool_calls. */
  arguments: Record<string, unknown>;
  result: unknown;
  /** True iff the tool's Python body raised; not inferred from `result`. */
  is_error: boolean;
}

export interface ApprovalRequiredEvent {
  type: "approval_required";
  id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  /**
   * Bare filenames under GET /api/previews/: a before/after render of the one
   * document edit this approval gates. Null when that does not apply.
   */
  before_preview: string | null;
  after_preview: string | null;
  /** Why auto mode handed this one to the user. */
  reviewer_note: string | null;
  /**
   * Set when a sub-agent is the one asking: the Background tasks panel shows it, not
   * the chat.
   */
  subagent_id?: string;
  subagent?: string;
}

/** A sub-agent of this conversation started, progressed, asked for approval or finished. */
export interface SubAgentsChangedEvent {
  type: "subagents_changed";
  task_id: string;
  status: string;
}

/** A background script of this conversation started or ended. */
export interface BackgroundTasksChangedEvent {
  type: "background_tasks_changed";
  task_id: string;
  status: string;
}

/** In plan mode, the model's finished plan, for the user to approve or send back. */
export interface PlanReadyEvent {
  type: "plan_ready";
  id: string;
  plan: string;
}

export interface QuestionOption {
  label: string;
  /** "" when the option has none. */
  description: string;
}

export interface QuestionSpec {
  question: string;
  header: string;
  options: QuestionOption[];
  multi_select: boolean;
}

/** ask_user_question: one or more questions, answered together with question_response. */
export interface QuestionRequiredEvent {
  type: "question_required";
  id: string;
  questions: QuestionSpec[];
}

/**
 * A scheduled run just started on this thread; `text` is the run's prompt (it never came
 * from this tab, so there is no local echo).
 */
export interface ScheduledRunStartedEvent {
  type: "scheduled_run_started";
  text: string;
}

/** One condition of a check step (or an approval's `when`). */
export interface WorkflowCheck {
  held: boolean;
  left: unknown;
  right: unknown;
}

/** A waiting step asking to be allowed a folder or site. */
export interface WorkflowPermission {
  kind: "folder" | "site";
  target: string;
  message: string;
}

/** One step of one workflow run (`workflows.engine.StepRecord.to_dict()`). */
export interface WorkflowStepRecord {
  step_id: string;
  status: "pending" | "running" | "done" | "failed" | "skipped" | "waiting";
  started_at: string | null;
  finished_at: string | null;
  output: unknown;
  error: string | null;
  checks: WorkflowCheck[] | null;
  /** What the person who answered an approval step wrote. */
  note: string | null;
  /**
   * Which pass of each loop around the step this is, outermost first; empty outside
   * loops.
   */
  iteration: number[];
  permission: WorkflowPermission | null;
}

/** One step of a workflow run on this thread started, finished, failed or began waiting. */
export interface WorkflowStepEvent {
  type: "workflow_step";
  run_id: string;
  record: WorkflowStepRecord;
}

/** A step of a test_workflow run started or ended; `done` of `total` steps have finished. */
export interface WorkflowTestProgressEvent {
  type: "workflow_test_progress";
  tool_call_id: string;
  step: string;
  status: string;
  done: number;
  total: number;
}

/**
 * create_scheduled_task's arguments as the model drafted them, or for edit_scheduled_task
 * the whole task as it would be saved. Nothing is saved until the user reviews it.
 */
export interface TaskDraft {
  name?: string;
  kind?: string;
  at?: string;
  prompt?: string;
  weekday?: number | null;
  day_of_month?: number | null;
  start_date?: string | null;
  model?: string | null;
  approval_mode?: string;
  /**
   * Set when this is a change to a saved task: which saved task, and which fields
   * change.
   */
  trigger_id?: string;
  changed?: string[];
}

/** Answered with question_response. */
export interface TaskDraftRequiredEvent {
  type: "task_draft_required";
  id: string;
  draft: TaskDraft;
}

export interface UsageEvent {
  type: "usage";
  total_tokens: number;
  /**
   * The three cache fields are present only when the provider reported prompt-cache
   * stats for this call; absent, not zero, when nothing was reported.
   */
  cache_read_tokens?: number;
  input_tokens?: number;
  cache_hit_rate?: number;
}

export interface TasksChangedEvent {
  type: "tasks_changed";
}

/**
 * The server started a turn of its own (a background sub-agent reporting how it ended)
 * with `text` as the turn's message.
 */
export interface TurnStartedEvent {
  type: "turn_started";
  text: string;
}

/** The conversation got a title from its first exchange. */
export interface ThreadTitledEvent {
  type: "thread_titled";
  title: string;
}

/** The message the person is most likely to send next, for the message box. */
export interface PromptSuggestionEvent {
  type: "prompt_suggestion";
  text: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

/**
 * A chat bubble from the assistant: the final answer to a turn, and also the /saveskill
 * curator's questions and previews.
 */
export interface AgentMessageEvent {
  type: "agent_message";
  text: string;
}

export interface CompactedEvent {
  type: "compacted";
  before: number;
  after: number;
  elapsed_ms: number;
}

export interface ClearedEvent {
  type: "cleared";
}

/** Confirms a rewind_message truncation happened. */
export interface RewoundEvent {
  type: "rewound";
  index: number;
}

/**
 * /saveskill's success confirmation. `slug` is the skill's directory name and its /<slug>
 * force-load token.
 */
export interface SkillSavedEvent {
  type: "skill_saved";
  name: string;
  slug: string;
}

/** Notes the user added mid-turn, now read by the model. */
export interface SteersDeliveredEvent {
  type: "steers_delivered";
  ids: string[];
}

/** Notes the turn ended before reading: sent as the next message, `text`. */
export interface SteersRequeuedEvent {
  type: "steers_requeued";
  ids: string[];
  text: string;
}

export type ServerEvent =
  | StateEvent
  | HistoryEvent
  | OlderMessagesEvent
  | AgentDeltaEvent
  | ToolStartedEvent
  | ToolResultEvent
  | ApprovalRequiredEvent
  | SubAgentsChangedEvent
  | BackgroundTasksChangedEvent
  | PlanReadyEvent
  | QuestionRequiredEvent
  | ScheduledRunStartedEvent
  | WorkflowStepEvent
  | WorkflowTestProgressEvent
  | TaskDraftRequiredEvent
  | UsageEvent
  | TasksChangedEvent
  | TurnStartedEvent
  | ThreadTitledEvent
  | PromptSuggestionEvent
  | ErrorEvent
  | AgentMessageEvent
  | CompactedEvent
  | ClearedEvent
  | RewoundEvent
  | SkillSavedEvent
  | SteersDeliveredEvent
  | SteersRequeuedEvent;

/**
 * Slash commands are plain `text` here, parsed server-side. `images` are base64 data URLs;
 * uploaded files go through POST /api/upload instead.
 */
export interface UserMessageOut {
  type: "user_message";
  text: string;
  images?: string[];
  /**
   * The first message of a conversation started from the Artifacts page: what it is
   * to make.
   */
  artifact?: "docs" | "slides" | "sheets";
}

/**
 * Edit an earlier user turn and regenerate from there. `index` is 0-based over the
 * history's "user" entries. The same events a fresh user_message would produce follow;
 * there is no dedicated confirmation.
 */
export interface EditMessageOut {
  type: "edit_message";
  index: number;
  text: string;
  images?: string[];
}

/**
 * Truncate back to before the user turn at `index` without rerunning it; answered with
 * `rewound`.
 */
export interface RewindMessageOut {
  type: "rewind_message";
  index: number;
}

export interface ApprovalResponseOut {
  type: "approval_response";
  id: string;
  approved: boolean;
  /** "task": allow this kind of action for the rest of the code task. */
  scope?: "task";
}

/** Answer to a plan or task draft. */
export interface QuestionAnswerOut {
  type: "question_response";
  id: string;
  answer: string;
}

/**
 * ask_user_question's answers, one per question (a multi-select one's choices joined by ",
 * ", null for a skipped one).
 */
export interface QuestionAnswersOut {
  type: "question_response";
  id: string;
  answers: (string | null)[];
}

/** The user closed the questions. */
export interface QuestionDismissedOut {
  type: "question_response";
  id: string;
  dismissed: true;
}

export type QuestionResponseOut =
  | QuestionAnswerOut
  | QuestionAnswersOut
  | QuestionDismissedOut;

/** Cooperative stop; also denies any pending approval. */
export interface StopOut {
  type: "stop";
}

/**
 * `model` is a "provider:model" string; `effort`, when given, changes the level too (the
 * model stays the same to change only the level). Answered with `state`, or `error`
 * leaving both as they were.
 */
export interface SwitchModelOut {
  type: "switch_model";
  model: string;
  effort?: "low" | "medium" | "high" | "extra" | "max" | "ultra";
}

/**
 * Replaces the conversation's folders, the main one first; empty goes back to the default
 * workspace. Answered with `state`, or `error` leaving them as they were.
 */
export interface SetFoldersOut {
  type: "set_folders";
  folders: string[];
}

/** One more folder, keeping the ones the conversation has. */
export interface AddFolderOut {
  type: "add_folder";
  folder: string;
}

/** Reveals one more pre-/compact epoch; answered with `older_messages`. */
export interface LoadOlderMessagesOut {
  type: "load_older_messages";
}

/**
 * A note for the turn in progress: the model reads it before its next step. A null text
 * takes the note back.
 */
export interface SteerOut {
  type: "steer";
  id: string;
  text: string | null;
}

export type ClientMessage =
  | UserMessageOut
  | SteerOut
  | EditMessageOut
  | RewindMessageOut
  | ApprovalResponseOut
  | QuestionAnswerOut
  | QuestionAnswersOut
  | QuestionDismissedOut
  | StopOut
  | SwitchModelOut
  | SetFoldersOut
  | AddFolderOut
  | LoadOlderMessagesOut;
