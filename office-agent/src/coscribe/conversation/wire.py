"""The chat WebSocket's messages, one TypedDict per `type`.

This is the per-thread chat socket (`/ws/{thread_id}`); the browser panel's socket and the
desktop shell's background-event stream speak their own protocols. The server sends plain
dicts, so this module is the one place their shape is written down: `tests/wire_check.py`
validates every payload the test suite sends against it, and a field renamed in
`session.py` without a change here fails a test. A new event is added here first, then sent.

Stdlib only: `conversation` must not import FastAPI or pydantic. A docstring on a
TypedDict says what the message means; keep the types to what a TypeScript
interface can say (str, bool, int, float, None, list, dict, Literal, unions and
other TypedDicts).
"""

from typing import Any, Literal, NotRequired, TypedDict, get_args, get_type_hints

# ---------------------------------------------------------------------------
# Server -> client
# ---------------------------------------------------------------------------

# How hard the model thinks (runtime_lg/effort.py LEVELS; a test keeps the two equal).
Effort = Literal["low", "medium", "high", "extra", "max", "ultra"]


class StateEvent(TypedDict):
    """The conversation's settings, sent on connect and after each change."""

    type: Literal["state"]
    plan_mode: bool
    accept_edits: bool
    # A reviewer model decides risky calls instead of the user.
    auto_mode: bool
    model: str
    effort: Effort
    # The model's own level that `effort` runs as (`xhigh` for extra, for example); None when the
    # model takes no effort setting.
    effort_runs_as: str | None
    context_window: int
    # Skills offered in this thread's instructions: the global on/off set, re-read at
    # the start of every turn.
    enabled_skills: list[str]
    # The thread's main folder; a thread with no folders falls back to the server's
    # default workspace.
    workspace_root: str
    # Whether workspace_root is a folder this conversation chose, not the default.
    workspace_explicit: bool
    # The folders this conversation works in, the main one first; empty while it uses
    # the default workspace.
    folders: list[str]
    # The connected connectors' tool names.
    connector_tools: list[str]
    # Only on the state sent right after connecting: whether a turn is already
    # running on this thread (typically a scheduled run), so the page shows it as
    # running.
    turn_in_flight: NotRequired[bool]


class UserEntry(TypedDict):
    kind: Literal["user"]
    text: str
    images: NotRequired[list[str]]


class SteerEntry(TypedDict):
    """A note the user added while a reply was being worked on."""

    kind: Literal["steer"]
    text: str
    images: NotRequired[list[str]]


class AgentEntry(TypedDict):
    kind: Literal["agent"]
    text: str


class ToolEntry(TypedDict):
    kind: Literal["tool"]
    tool_name: str
    arguments: dict[str, Any]
    result: Any
    # True iff the tool's Python body raised (the checkpointed ToolMessage's status).
    is_error: bool


HistoryEntry = UserEntry | SteerEntry | AgentEntry | ToolEntry


class HistoryEvent(TypedDict):
    """The thread's checkpointed messages, replayed once after connecting."""

    type: Literal["history"]
    entries: list[HistoryEntry]
    # Whether the checkpoint starts with a compaction note, i.e. whether
    # load_older_messages has anything to find.
    has_older: bool


class OlderMessagesEvent(TypedDict):
    """Answer to load_older_messages: one whole pre-/compact epoch. `has_more` is a
    "try again" hint, true whenever this call found a batch; an empty `entries` is
    the one unambiguous "nothing earlier"."""

    type: Literal["older_messages"]
    entries: list[HistoryEntry]
    has_more: bool


class AgentDeltaEvent(TypedDict):
    type: Literal["agent_delta"]
    text: str


class ToolStartedEvent(TypedDict):
    """A call about to run; its tool_result follows. Not sent for a call waiting on
    approval (approval_required shows that one)."""

    type: Literal["tool_started"]
    tool_name: str
    arguments: dict[str, Any]


class ToolResultEvent(TypedDict):
    type: Literal["tool_result"]
    tool_name: str
    # The call's own arguments, taken from the preceding AIMessage's tool_calls.
    arguments: dict[str, Any]
    result: Any
    # True iff the tool's Python body raised; not inferred from `result`.
    is_error: bool


class ApprovalRequiredEvent(TypedDict):
    type: Literal["approval_required"]
    id: str
    tool_name: str
    arguments: dict[str, Any]
    # Bare filenames under GET /api/previews/: a before/after render of the one
    # document edit this approval gates. Null when that does not apply.
    before_preview: str | None
    after_preview: str | None
    # Why auto mode handed this one to the user.
    reviewer_note: str | None
    # Set when a sub-agent is the one asking: the Background tasks panel shows it,
    # not the chat.
    subagent_id: NotRequired[str]
    subagent: NotRequired[str]


class SubAgentsChangedEvent(TypedDict):
    """A sub-agent of this conversation started, progressed, asked for approval or
    finished."""

    type: Literal["subagents_changed"]
    task_id: str
    status: str


class BackgroundTasksChangedEvent(TypedDict):
    """A background script of this conversation started or ended."""

    type: Literal["background_tasks_changed"]
    task_id: str
    status: str


class PlanReadyEvent(TypedDict):
    """In plan mode, the model's finished plan, for the user to approve or send
    back."""

    type: Literal["plan_ready"]
    id: str
    plan: str


class QuestionOption(TypedDict):
    label: str
    # "" when the option has none.
    description: str


class QuestionSpec(TypedDict):
    question: str
    header: str
    options: list[QuestionOption]
    multi_select: bool


class QuestionRequiredEvent(TypedDict):
    """ask_user_question: one or more questions, answered together with
    question_response."""

    type: Literal["question_required"]
    id: str
    questions: list[QuestionSpec]


class ScheduledRunStartedEvent(TypedDict):
    """A scheduled run just started on this thread; `text` is the run's prompt (it
    never came from this tab, so there is no local echo)."""

    type: Literal["scheduled_run_started"]
    text: str


class WorkflowCheck(TypedDict):
    """One condition of a check step (or an approval's `when`)."""

    held: bool
    left: Any
    right: Any


class WorkflowPermission(TypedDict):
    """A waiting step asking to be allowed a folder or site."""

    kind: Literal["folder", "site"]
    target: str
    message: str


class WorkflowStepRecord(TypedDict):
    """One step of one workflow run (`workflows.engine.StepRecord.to_dict()`)."""

    step_id: str
    status: Literal["pending", "running", "done", "failed", "skipped", "waiting"]
    started_at: str | None
    finished_at: str | None
    output: Any
    error: str | None
    checks: list[WorkflowCheck] | None
    # What the person who answered an approval step wrote.
    note: str | None
    # Which pass of each loop around the step this is, outermost first; empty outside
    # loops.
    iteration: list[int]
    permission: WorkflowPermission | None


class WorkflowStepEvent(TypedDict):
    """One step of a workflow run on this thread started, finished, failed or began
    waiting."""

    type: Literal["workflow_step"]
    run_id: str
    record: WorkflowStepRecord


class WorkflowTestProgressEvent(TypedDict):
    """A step of a test_workflow run started or ended; `done` of `total` steps have
    finished."""

    type: Literal["workflow_test_progress"]
    tool_call_id: str
    step: str
    status: str
    done: int
    total: int


class TaskDraft(TypedDict):
    """create_scheduled_task's arguments as the model drafted them, or for
    edit_scheduled_task the whole task as it would be saved. Nothing is saved until
    the user reviews it."""

    name: NotRequired[str]
    kind: NotRequired[str]
    at: NotRequired[str]
    prompt: NotRequired[str]
    weekday: NotRequired[int | None]
    day_of_month: NotRequired[int | None]
    start_date: NotRequired[str | None]
    model: NotRequired[str | None]
    approval_mode: NotRequired[str]
    # Set when this is a change to a saved task: which saved task, and which fields
    # change.
    trigger_id: NotRequired[str]
    changed: NotRequired[list[str]]


class TaskDraftRequiredEvent(TypedDict):
    """Answered with question_response."""

    type: Literal["task_draft_required"]
    id: str
    draft: TaskDraft


class UsageEvent(TypedDict):
    type: Literal["usage"]
    total_tokens: int
    # The three cache fields are present only when the provider reported prompt-cache
    # stats for this call; absent, not zero, when nothing was reported.
    cache_read_tokens: NotRequired[int]
    input_tokens: NotRequired[int]
    cache_hit_rate: NotRequired[float]


class TasksChangedEvent(TypedDict):
    type: Literal["tasks_changed"]


class TurnStartedEvent(TypedDict):
    """The server started a turn of its own (a background sub-agent reporting how it
    ended) with `text` as the turn's message."""

    type: Literal["turn_started"]
    text: str


class ThreadTitledEvent(TypedDict):
    """The conversation got a title from its first exchange."""

    type: Literal["thread_titled"]
    title: str


class ErrorEvent(TypedDict):
    type: Literal["error"]
    message: str


class AgentMessageEvent(TypedDict):
    """A chat bubble from the assistant: the final answer to a turn, and also the
    /saveskill curator's questions and previews."""

    type: Literal["agent_message"]
    text: str


class CompactedEvent(TypedDict):
    type: Literal["compacted"]
    before: int
    after: int
    elapsed_ms: int


class ClearedEvent(TypedDict):
    type: Literal["cleared"]


class RewoundEvent(TypedDict):
    """Confirms a rewind_message truncation happened."""

    type: Literal["rewound"]
    index: int


class SkillSavedEvent(TypedDict):
    """/saveskill's success confirmation. `slug` is the skill's directory name and
    its /<slug> force-load token."""

    type: Literal["skill_saved"]
    name: str
    slug: str


class SteersDeliveredEvent(TypedDict):
    """Notes the user added mid-turn, now read by the model."""

    type: Literal["steers_delivered"]
    ids: list[str]


class SteersRequeuedEvent(TypedDict):
    """Notes the turn ended before reading: sent as the next message, `text`."""

    type: Literal["steers_requeued"]
    ids: list[str]
    text: str


ServerEvent = (
    StateEvent
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
    | ErrorEvent
    | AgentMessageEvent
    | CompactedEvent
    | ClearedEvent
    | RewoundEvent
    | SkillSavedEvent
    | SteersDeliveredEvent
    | SteersRequeuedEvent
)

# ---------------------------------------------------------------------------
# Client -> server (parsed in web/routes/ws.py)
# ---------------------------------------------------------------------------


class UserMessageOut(TypedDict):
    """Slash commands are plain `text` here, parsed server-side. `images` are base64
    data URLs; uploaded files go through POST /api/upload instead."""

    type: Literal["user_message"]
    text: str
    images: NotRequired[list[str]]
    # The first message of a conversation started from the Artifacts page: what it is to make.
    artifact: NotRequired[Literal["docs", "slides", "sheets"]]


class EditMessageOut(TypedDict):
    """Edit an earlier user turn and regenerate from there. `index` is 0-based over
    the history's "user" entries. The same events a fresh user_message would produce
    follow; there is no dedicated confirmation."""

    type: Literal["edit_message"]
    index: int
    text: str
    images: NotRequired[list[str]]


class RewindMessageOut(TypedDict):
    """Truncate back to before the user turn at `index` without rerunning it;
    answered with `rewound`."""

    type: Literal["rewind_message"]
    index: int


class ApprovalResponseOut(TypedDict):
    type: Literal["approval_response"]
    id: str
    approved: bool
    # "task": allow this kind of action for the rest of the code task.
    scope: NotRequired[Literal["task"]]


class QuestionAnswerOut(TypedDict):
    """Answer to a plan or task draft."""

    type: Literal["question_response"]
    id: str
    answer: str


class QuestionAnswersOut(TypedDict):
    """ask_user_question's answers, one per question (a multi-select one's choices
    joined by ", ", null for a skipped one)."""

    type: Literal["question_response"]
    id: str
    answers: list[str | None]


class QuestionDismissedOut(TypedDict):
    """The user closed the questions."""

    type: Literal["question_response"]
    id: str
    dismissed: Literal[True]


QuestionResponseOut = QuestionAnswerOut | QuestionAnswersOut | QuestionDismissedOut


class StopOut(TypedDict):
    """Cooperative stop; also denies any pending approval."""

    type: Literal["stop"]


class SwitchModelOut(TypedDict):
    """`model` is a "provider:model" string; `effort`, when given, changes the level too (the
    model stays the same to change only the level). Answered with `state`, or `error` leaving
    both as they were."""

    type: Literal["switch_model"]
    model: str
    effort: NotRequired[Effort]


class SetFoldersOut(TypedDict):
    """Replaces the conversation's folders, the main one first; empty goes back to
    the default workspace. Answered with `state`, or `error` leaving them as they
    were."""

    type: Literal["set_folders"]
    folders: list[str]


class AddFolderOut(TypedDict):
    """One more folder, keeping the ones the conversation has."""

    type: Literal["add_folder"]
    folder: str


class LoadOlderMessagesOut(TypedDict):
    """Reveals one more pre-/compact epoch; answered with `older_messages`."""

    type: Literal["load_older_messages"]


class SteerOut(TypedDict):
    """A note for the turn in progress: the model reads it before its next step. A null text
    takes the note back."""

    type: Literal["steer"]
    id: str
    text: str | None


ClientMessage = (
    UserMessageOut
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
    | LoadOlderMessagesOut
)


def _by_type(union: Any) -> dict[str, list[Any]]:
    classes: dict[str, list[Any]] = {}
    for cls in get_args(union):
        (name,) = get_args(get_type_hints(cls)["type"])
        classes.setdefault(name, []).append(cls)
    return classes


# A `type` literal to the TypedDicts that carry it (several only for
# question_response, whose three shapes differ by key).
SERVER_EVENTS = _by_type(ServerEvent)
CLIENT_MESSAGES = _by_type(ClientMessage)
