"""ChatSessionLG: the web equivalent of cli.py's chat() loop body, built
on runtime_lg instead of runtime/ (see runtime_lg/README.md, Phase 3).

Mirrors conversation/session.py's ChatSession public shape (handle_user_message,
resolve_approval, send_state) closely enough that app.py's WS handler is
nearly identical to app.py's -- but the internals are native async
(agent.astream/aget_state) instead of the queue.Queue/asyncio.to_thread
bridging ChatSession needs only because Runner.run_sync is synchronous.

/plan, /accept-edits, /compact, /clear, /stop, model switching, and Hooks
are supported here (see runtime_lg/README.md's "Plan mode, accept-edits,
compact, and Hooks under runtime_lg" section for the design of the first
four; /stop and switch_model follow the same "port the contract, adapt the
mechanism to a compiled graph" approach -- /stop is cooperative, checked at
_stream_turn/_decide_action_request's own yield points; switch_model rebuilds
self.lg_agent against the same checkpointer/thread_id rather than mutating
a model string in place, since create_agent() bakes the model into a fixed
compiled graph at construction time). Threshold-triggered *automatic*
compaction (Settings.auto_compact_threshold) and a turn cap
(Settings.max_turns) *are* both wired in too -- see _build_lg_agent below,
which passes both through to build_langgraph_agent as
SummarizationMiddleware/ModelCallLimitMiddleware. Still narrower than
ChatSession in one documented way: Hooks configured on a top-level
session don't propagate into spawn_agent's/review_work's own nested
sub-agent graphs -- a sub-agent's own tool calls run without PreToolUse/
PostToolUse checks. spawn_agent/review_work delegation *is* wired in
(see runtime_lg/README.md's "spawn_agent's nested-interrupt bridge" section --
live-verified against Gemini before being added here, including that a
nested approval bridges up through _resolve_pending_approvals below with
zero changes needed, since the bridged interrupt's payload shape matches
HumanInTheLoopMiddleware's own exactly).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from asyncio import Future
from collections import defaultdict
from collections.abc import Callable, Sequence
from functools import cached_property
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.messages.ai import UsageMetadata
from langchain_core.tools import BaseTool
from langgraph.constants import TAG_NOSTREAM
from langgraph.types import Command

from ..code_runtime import code_service
from ..config import Settings
from ..coordinator import CORE_TOOL_NAMES, build_coordinator_agent, conversation_context
from ..runtime import (
    LLMClient,
    empty_hooks_config,
    get_tool_metadata,
)
from ..runtime.provider_config import load_custom_providers
from ..runtime.secret_store import SessionEnvironments, redactor
from ..runtime_lg import (
    ORPHANED_TOOL_CALL_NOTE,
    SilentSocket,
    SubAgentHost,
    build_delegation_tools,
    build_langgraph_agent,
    build_review_work_tool,
    for_conversation,
    keeps_tool_list_fixed,
    resolve_chat_model,
    select_reviewer_tools,
    tool_name,
)
from ..runtime_lg import extract_text as _extract_text
from ..runtime_lg import tool_result_value as _tool_result_value
from ..runtime_lg.audit import AutoApproveReason
from ..runtime_lg.auto_review import Verdict
from ..runtime_lg.code_agent import (
    CODE_APPROVAL_RISKS,
    CODE_TASK_TOOL,
    CodeTaskContext,
    build_code_task_tool,
)
from ..runtime_lg.exec_policy import EXEC_POLICY_TOOL_NAMES, ExecPolicy, load_exec_policy
from ..runtime_lg.messages import (
    ACCEPT_EDITS_MODE_NOTE,
    AUTO_MODE_NOTE,
    NORMAL_MODE_NOTE,
    PLAN_MODE_NOTE,
    context_note,
    current_date_note,
    language_note,
    last_conversation_context,
    strip_mode_note,
)
from ..runtime_lg.tool_deferral import (
    bound_tool_names,
    build_search_tools_tool,
    build_use_tool_tool,
    unwrap_use_tool_call,
)
from ..tools import (
    QUESTION_TOOL_NAMES,
    format_skill_listing,
    load_builtin_skills,
    load_skills,
)
from ..tools._workspace import WorkspaceScope
from ..tools.background_tasks import BackgroundTask, set_change_listener
from ..tools.browser import BROWSER_HOST
from ..tools.conversations import set_inbox_listener
from ..tools.http_request import build_http_tools
from ..tools.scheduled_tasks import (
    TASK_DRAFT_TOOL_NAMES,
    ScheduledTriggerStore,
    parse_run_thread_id,
)
from ..tools.skill_catalog import enabled_skill_names
from ..tools.subagent_tasks import SubAgentTask
from ..workflows import StepContext, WorkflowDraft
from . import tool_hooks
from .activity import summarize_activity, summarize_workflow_run
from .approvals import ApprovalDecider, can_resolve_approvals
from .context_usage import build_context_breakdown
from .edit_preview import build_document_edit_preview
from .events import EventSink
from .history import ConversationHistory
from .history import close_orphaned_tool_calls as _close_orphaned_tool_calls
from .prompts import INIT_PROMPT
from .reconfigure import SessionReconfigurer
from .skill_save import SkillSave
from .subagents import _MAX_REPORT_TURNS_IN_ROW as _MAX_REPORT_TURNS_IN_ROW
from .subagents import SubAgentApprovalChannel, SubAgentReporter
from .thread_meta import ThreadMetaStore
from .turn_lock import TurnLock
from .turn_text import (
    TITLE_INSTRUCTIONS,
    build_instructions,
    clean_title,
    format_reply,
    usage_event,
)
from .workflow_drafting import WorkflowDrafting

logger = logging.getLogger(__name__)

# Tests construct the channel by this name.
_SubAgentApprovalChannel = SubAgentApprovalChannel

# /saveworkflow <name>: the model distills the conversation into a draft
# scheduled task via create_scheduled_task, which the user then reviews.
SAVE_WORKFLOW_PROMPT = (
    'Save what we did in this conversation as a reusable workflow named "{name}": '
    'call create_scheduled_task with name="{name}", kind="manual" unless I asked '
    "for a schedule, and a prompt distilled from this conversation -- the steps and "
    "inputs that actually worked, pitfalls we ran into and how to avoid them, and "
    "the expected output. Leave out dead ends and unrelated chatter. If there's no "
    "repeatable task in this conversation yet, ask me what to save instead."
)

_ORPHANED_TOOL_CALL_NOTE = ORPHANED_TOOL_CALL_NOTE


def _new_draft_id() -> str:
    return uuid.uuid4().hex[:8]


def _risks_of_gated_tools(lg_tools: list[Any]) -> dict[str, str]:
    """Every approval-gated tool's name -> its risk category, which the
    scheduled-run approval tiers key on (see _auto_approves)."""
    risks: dict[str, str] = {}
    for t in lg_tools:
        metadata = get_tool_metadata(cast(Any, t))
        if metadata.requires_approval:
            risks[tool_name(t)] = metadata.risk_category
        # The code module's commands and file changes are asked about under
        # these names; a name missing here would be approved without asking.
        if tool_name(t) == CODE_TASK_TOOL:
            risks.update(CODE_APPROVAL_RISKS)
    return risks


# langchain_google_genai's gRPC channel accumulates something into the
# outgoing x-goog-api-client metadata header across repeated calls on the
# same long-lived channel -- an unresolved upstream bug in google-auth-
# library-python (see e.g. googleapis/python-aiplatform#3965,
# langchain-ai/langchain-google#306), not fixable from this codebase.
# Eventually the header outgrows grpc's default metadata soft limit and
# every further call on that channel fails with this exact message --
# waiting or retrying on the *same* channel never helps, since this
# session's ChatGoogleGenerativeAI client (and its channel) lives as long
# as the thread does. Forcing transport="rest" to dodge gRPC state
# entirely was already tried and reverted for a different real bug in
# this SDK version's async REST streaming path -- see providers.py's own
# comment. The narrow fix instead: recognize this one signature and
# recreate the client (a fresh channel starts the header at zero) before
# retrying.
_GRPC_METADATA_OVERFLOW_SIGNATURE = "metadata size exceeds soft limit"


class ChatSessionLG:
    def __init__(
        self,
        *,
        thread_id: str,
        settings: Settings,
        context_window_client: LLMClient,
        custom_providers: dict[str, dict[str, str]],
        extra_tools: list[Any],
        checkpointer: Any,
        hooks_config: dict[str, list[str]] | None = None,
        enabled_skill_names: set[str] | None = None,
        workspace_root: Path | None = None,
        workspace_explicit: bool = False,
        extra_folders: list[Path] | None = None,
        configured_models: Callable[[], list[str]] | None = None,
    ) -> None:
        self.thread_id = thread_id
        # "provider:model" for every configured provider -- what a sub-agent
        # may be run on.
        self._configured_models = configured_models or (lambda: [self._model_string])
        # The socket of the turn now (or last) running: where a sub-agent's
        # approval goes when no browser tab is watching (the CLI).
        self._turn_websocket: Any = None
        # Approval request ids that belong to sub-agents, which a Stop of
        # the parent's turn must not deny.
        self._subagent_request_ids: set[str] = set()
        # Background sub-agent runs whose end is being reported, and the
        # tasks doing it (held so they aren't garbage-collected mid-turn).
        self._reporting_subagents: set[str] = set()
        self._report_tasks: set[asyncio.Task[None]] = set()
        # Report turns since the user last spoke: each can start another
        # sub-agent, whose report starts another turn, with nobody there.
        self._report_turns_in_row = 0
        self._delivering_inbox = False
        self._loop: asyncio.AbstractEventLoop | None = None
        with contextlib.suppress(RuntimeError):
            self._loop = asyncio.get_running_loop()
        self.settings = settings
        # None (the old default, still used by anything that hasn't been
        # taught about per-thread workspaces) falls back to the global
        # settings.workspace_root -- see coordinator.py's identical
        # fallback in build_coordinator_agent.
        self.workspace_root: Path = workspace_root or settings.workspace_root
        # A flag, not a comparison with settings.workspace_root: a user can
        # deliberately choose the default folder, and the UI should show it
        # as chosen.
        self._workspace_explicit = workspace_explicit
        # Folders added after the first; readable and writable like it.
        self.extra_folders: list[Path] = list(extra_folders or [])
        self._context_window_client = context_window_client
        self._context_window: int | None = None
        self._pending_approvals: dict[str, Future[bool]] = {}
        # The code module's approvals: which (task, action) a pending card
        # is for, and what the person has allowed for a whole task.
        self._code_requests: dict[str, tuple[str, str]] = {}
        self._code_task_allowances: set[tuple[str, str]] = set()
        # A question's answer is one entry per question, or None when the
        # user closed them; the other requests (plans, drafts) and a stop
        # answer with a string.
        self._pending_questions: dict[str, Future[Any]] = {}
        self.hooks_config: dict[str, list[str]] = hooks_config or empty_hooks_config()
        self.plan_mode = False
        self.accept_edits = False
        # Auto mode: a reviewer model decides risky calls in the user's
        # place. After 3 blocks in a row or 20 in all it pauses and the
        # user is asked, as in Claude Code; the user approving one resumes it.
        self.auto_mode = False
        self._auto_blocks_in_row = 0
        self._auto_blocks_total = 0
        self._auto_paused = False
        if settings.default_permission_mode != "manual" and parse_run_thread_id(thread_id) is None:
            self._toggle_mode(settings.default_permission_mode)
        # Reset at the top of every handle_user_message call -- see
        # _stream_turn's docstring for why this exists (recovering a tool
        # call's arguments for the PostToolUse hook payload, which the
        # ToolMessage carrying its result doesn't itself include).
        self._pending_tool_args: dict[str, list[dict[str, Any]]] = defaultdict(list)
        # Cooperative /stop flag -- see request_stop's docstring. Reset at
        # the start of every handle_user_message call.
        self._stop_requested = False
        # Most recent model-response segment's real usage_metadata (see
        # _stream_turn's _capture_segment_usage) -- not reset per-turn like
        # _pending_tool_args/_stop_requested above, since it's read once
        # after the whole turn (including any approval-resume continuation)
        # finishes, not checked mid-turn. None until the first real segment
        # completes, or if the active model never populates usage_metadata.
        self._last_usage_metadata: UsageMetadata | None = None
        # conversation/session.py's ws_endpoint dispatches each incoming
        # "user_message" via asyncio.create_task without awaiting it, so it
        # can go straight back to receiving the next one -- otherwise a
        # turn blocked on approval would freeze the whole socket, including
        # approval_response messages for that same turn (app.py's
        # ws_endpoint does the identical thing). Without this lock, a
        # second message sent while the first is still running would start
        # a fully concurrent second handle_user_message call against the
        # same self.lg_agent/self.config -- each mutating the same shared
        # instance state (_pending_tool_args, _stop_requested) and issuing
        # concurrent astream()/aget_state() calls against the identical
        # checkpointed thread, racing and interleaving their output. Same
        # lock ChatSession already has for the exact same reason; this
        # runtime just never had it ported over until a concurrency review
        # caught the gap. resolve_approval/request_stop are deliberately
        # NOT gated by this lock, same as ChatSession's identical methods
        # -- they have to be able to reach whichever turn is *currently*
        # in flight, not queue behind it.
        self._turn_lock = TurnLock(self._turn_lock_changed)
        # Notes the user sent during a turn, (id, text), not yet read by
        # the model.
        self._steers: list[tuple[str, str]] = []
        # The task currently holding _turn_lock (handle_user_message or
        # resume_after_reconnect), if any -- see abandon_orphaned_turn's
        # docstring for why this exists: a turn lock alone would let an
        # orphaned task (one whose websocket died mid-approval-wait, so
        # nothing can ever resolve its pending Future) block every future
        # turn on this thread_id forever, including a genuine reconnect's
        # own attempt to redeliver that same pending approval.
        self._current_turn_task: asyncio.Task[None] | None = None
        # None = no /saveskill curation in progress; otherwise awaiting the
        # user's answer to a clarifying question or confirmation of a
        # proposed save -- see _handle_pending_skill_save_proposal.
        self.pending_save_skill_proposal: dict[str, Any] | None = None

        self.enabled_skill_names: set[str] = set(enabled_skill_names or ())
        agent = self._build_agent()
        # Unrestricted by enabled_skill_names deliberately -- a /<slug>
        # slash command is an explicit, one-off user request to follow
        # that skill for this message, distinct from the passive "is it
        # listed in instructions" toggle set_enabled_skills controls
        # below. Keyed by SkillInfo.slug (a single command-safe token,
        # e.g. "skill-creator"), not skill.name -- every current built-in
        # skill's display name has a space in it ("Skill Creator", "Word
        # Documents", ...), which a bare `.lower()` on the name can never
        # match against the single word _handle_user_message_locked below
        # actually parses out of "/<word> <rest>". Real, previously-
        # shipped-but-untested bug: the frontend's own autocomplete
        # (Composer.tsx's selectAutocomplete) inserted the literal display
        # name including its space, so selecting a multi-word skill from
        # the dropdown produced text this lookup could never match --
        # confirmed by reading through both sides together, not by a
        # live report. Distinct from web/app.py's *other*, separately-
        # scoped `skills_by_name` (the enable/disable toggle, correctly
        # keyed by display name -- that one was never broken).
        self.skills_by_slug = {
            skill.slug: skill for skill in load_builtin_skills() + load_skills(settings.skills_dir)
        }

        # Kept for switch_model, which needs to rebuild both the tool list
        # (spawn_agent/review_work are bound to a specific model) and the
        # compiled graph itself against a *new* model, reusing everything
        # else about this session unchanged (same checkpointer/thread_id,
        # same base tools, same instructions).
        self._checkpointer = checkpointer
        self._custom_providers = custom_providers
        self._base_tools: list[Callable[..., Any] | BaseTool] = list(agent.tools)
        # Kept separate from self._base_tools (not just concatenated once
        # here) because refresh_extra_tools below can replace this list
        # wholesale, independently, whenever an MCP connector connects/
        # disconnects live -- self._base_tools never needs rebuilding for
        # that. Combined back in by _build_lg_tools below (same treatment
        # spawn_agent/review_work already get).
        self._extra_tools: list[Callable[..., Any] | BaseTool] = list(extra_tools)
        self._title_task: asyncio.Task[None] | None = None
        self._instructions = agent.instructions or ""
        self._model_string = settings.default_model
        self._effort: str = settings.default_effort
        self.model, self._effort_runs_as = self._conversation_model(
            self._model_string, self._effort
        )
        lg_tools = self._build_lg_tools(self.model)
        # The *original* requires_approval set, computed independently of
        # what actually ends up in HumanInTheLoopMiddleware's interrupt_on
        # (which _build_lg_agent below may widen to include every tool, if
        # PreToolUse hooks are configured) -- plan mode needs to tell
        # "genuinely risky, blocked outright" apart from "only gated so a
        # hook gets a look," and this is the one place that distinction is
        # still visible. See _resolve_pending_approvals. Tool *names* don't
        # change across a model switch (same base tools, same spawn_agent/
        # review_work names every time), so this set is computed once here
        # and never needs recomputing anywhere else.
        self._gated_tool_risks = _risks_of_gated_tools(lg_tools)
        self.lg_agent = self._build_lg_agent(self.model, self._model_string, lg_tools)
        self.config = {"configurable": {"thread_id": thread_id}}
        # The currently-connected browser tab's websocket, if any -- set/
        # cleared by app.py's ws_endpoint around its own connection
        # lifetime, *not* threaded through every method call the way
        # every other websocket use in this class already is (see
        # notify_resync's own docstring for why this one specifically
        # needs a place to live outside any single call's stack).
        self._live_websocket: EventSink | None = None
        set_change_listener(self.thread_id, self._background_task_changed)
        set_inbox_listener(self.thread_id, self.schedule_inbox_delivery)
        # A reply is being worked on -- unlike the turn lock, not held for the
        # moments a reconnect or a folder change takes it.
        self.turn_running = False
        # The prompt of a scheduled run executing on this thread right now
        # (set by runtime_lg/scheduled_tasks.py). A tab that opens the run
        # just after it starts can connect before that prompt is
        # checkpointed -- send_history fills it in so the run never shows
        # up without its opening message.
        self.active_run_prompt: str | None = None
        # The executing scheduled run's approval_mode, also set by
        # runtime_lg/scheduled_tasks.py -- see _auto_approves.
        self.run_approval_mode: str | None = None
        # Gated tools the current turn may call without asking, set by
        # whoever started it for someone who isn't there to be asked.
        self.preapproved_tools: frozenset[str] = frozenset()
        self._offer_task: asyncio.Task[None] | None = None

    def _conversation_model(self, model_string: str, effort: str) -> tuple[Any, str | None]:
        return for_conversation(
            resolve_chat_model(model_string, self._custom_providers), self.thread_id, effort
        )

    def _build_lg_tools(self, model: Any) -> list[Callable[..., Any] | BaseTool]:
        # self._base_tools ("domain" tools) combined with self._extra_tools
        # (MCP connector tools -- see __init__'s comment on why these are
        # kept separate) *before* appending spawn_agent itself below -- a
        # sub-agent's own
        # selectable tool_names never includes spawn_agent, and does include
        # MCP tools.
        combined_tools = [*self._base_tools, *self._extra_tools]
        delegation_tools = build_delegation_tools(self._subagent_host(model), combined_tools)
        # The reviewer only ever gets read-only tools (document readers and
        # file listing/reading) -- independent verification of a generated
        # file's real content, never a way for it to change anything. See
        # select_reviewer_tools for why that also keeps it from pausing on
        # an approval.
        reviewer_tools = select_reviewer_tools(combined_tools)
        review_work_tool = build_review_work_tool(model, reviewer_tools, self.settings.state_dir)
        code_tools: list[Callable[..., Any]] = []
        if self.settings.code_module_enabled:
            code_tools.append(
                build_code_task_tool(
                    self._subagent_host(model),
                    CodeTaskContext(
                        service=lambda: code_service(self.settings),
                        model=lambda: self.settings.code_model or self._model_string,
                        folder=lambda: Path(self.workspace_root),
                        context_window=lambda: self._context_window_client.get_context_window(
                            self.settings.code_model or self._model_string
                        ),
                        env=lambda: SessionEnvironments(self.settings.state_dir).get(
                            self.thread_id
                        )["variables"],
                    ),
                )
            )
        return [
            *combined_tools,
            *delegation_tools,
            *code_tools,
            *build_http_tools(self.settings.state_dir, self.thread_id),
            review_work_tool,
            self._build_draft_workflow_tool(),
            self._build_revise_workflow_tool(),
            self._build_test_workflow_tool(),
        ]

    @cached_property
    def _subagents(self) -> SubAgentReporter:
        return SubAgentReporter(self)

    def _subagent_host(self, model: Any) -> SubAgentHost:
        return self._subagents._subagent_host(model)

    async def _subagent_changed(self, task: SubAgentTask) -> None:
        await self._subagents._subagent_changed(task)

    def _background_task_changed(self, task: BackgroundTask) -> None:
        self._subagents._background_task_changed(task)

    async def _report_subagent(self, task_id: str, reasons: list[str]) -> None:
        await self._subagents._report_subagent(task_id, reasons)

    def schedule_inbox_delivery(self) -> None:
        self._subagents.schedule_inbox_delivery()

    def _stop_waited_on_subagents(self) -> None:
        self._subagents._stop_waited_on_subagents()

    def _title_path(self) -> Path:
        # The same sidecar app.py's rename endpoint writes and list_threads
        # reads.
        return Path(self.settings.state_dir) / f"{self.thread_id}.title"

    def _wants_title(self) -> bool:
        return (
            self.settings.auto_title_threads
            and not self._stop_requested
            and parse_run_thread_id(self.thread_id) is None
            and not self._title_path().exists()
            and (self._title_task is None or self._title_task.done())
        )

    async def _name_thread(self, websocket: EventSink, first_message: str | None = None) -> None:
        """A short title from the conversation's first message, asked for as
        soon as it is sent so that a long first turn (or one waiting on the
        user) doesn't leave the raw message as the label; the end of the first
        turn asks again, with the reply, if that one got nothing."""
        try:
            first_user = first_message or ""
            last_reply = ""
            if first_message is None:
                state = await self.lg_agent.aget_state(self.config)
                messages = list(state.values.get("messages", [])) if state.values else []
                first_user = next(
                    (
                        strip_mode_note(_extract_text(m.content))
                        for m in messages
                        if m.type == "human"
                    ),
                    "",
                )
                last_reply = next(
                    (
                        _extract_text(m.content)
                        for m in reversed(messages)
                        if m.type == "ai" and _extract_text(m.content)
                    ),
                    "",
                )
            if not first_user.strip():
                return
            reply = await self.model.ainvoke(
                [
                    SystemMessage(content=TITLE_INSTRUCTIONS),
                    HumanMessage(
                        content=f"User: {first_user[:1500]}"
                        + (f"\n\nAssistant: {last_reply[:1500]}" if last_reply else "")
                    ),
                ],
                config={"tags": [TAG_NOSTREAM]},
            )
            title = clean_title(_extract_text(reply.content))
            if not title or self._title_path().exists():
                return
            self._title_path().parent.mkdir(parents=True, exist_ok=True)
            self._title_path().write_text(title, encoding="utf-8")
            await websocket.send_json({"type": "thread_titled", "title": title})
        except Exception:  # noqa: BLE001 -- a missing title is harmless; the first message stays the label
            logger.info("could not name thread %s", self.thread_id, exc_info=True)

    @cached_property
    def _drafting(self) -> WorkflowDrafting:
        return WorkflowDrafting(self)

    def _next_draft_id(self) -> str:
        return _new_draft_id()

    def _resolve_model(self, model_string: str) -> Any:
        return resolve_chat_model(model_string, self._custom_providers)

    def _build_draft_workflow_tool(self) -> BaseTool:
        return self._drafting._build_draft_workflow_tool()

    def _build_revise_workflow_tool(self) -> BaseTool:
        return self._drafting._build_revise_workflow_tool()

    def _build_test_workflow_tool(self) -> BaseTool:
        return self._drafting._build_test_workflow_tool()

    def _build_lg_agent(
        self, model: Any, model_string: str, lg_tools: list[Callable[..., Any] | BaseTool]
    ) -> Any:
        # When PreToolUse hooks are configured, route *every* tool call
        # through the same interrupt point -- not just the ones that
        # already require human approval -- so a hook gets the chance to
        # veto a low-risk tool too, not just a gated one.
        extra_interrupt_names = (
            [tool_name(t) for t in lg_tools] if self.hooks_config["PreToolUse"] else []
        )
        # `model_string` is taken as its own parameter rather than read from
        # self._model_string -- switch_model (below) calls this *before*
        # updating self._model_string (so a failed switch can revert
        # cleanly without ever having mutated it), so reading the field
        # here would silently compute auto_compact_tokens for the *old*
        # model on every switch. get_context_window is best-effort and
        # never raises (see LLMClient.get_context_window's own docstring),
        # so no try/except is needed around it here.
        auto_compact_tokens = max(
            1,
            int(
                self._context_window_client.get_context_window(model_string)
                * self.settings.auto_compact_threshold
            ),
        )
        core_names, defer = self._tool_binding(model_string, lg_tools)
        return build_langgraph_agent(
            model,
            lg_tools,
            build_instructions(self._instructions, defer_tools=defer),
            checkpointer=self._checkpointer,
            extra_interrupt_tool_names=extra_interrupt_names,
            question_tool_names=QUESTION_TOOL_NAMES | TASK_DRAFT_TOOL_NAMES,
            max_turns=self.settings.max_turns,
            auto_compact_tokens=auto_compact_tokens,
            defer_tools=defer,
            core_tool_names=core_names,
            take_steers=self._take_steers,
            redact=redactor(self.settings.state_dir),
        )

    def _tool_binding(
        self, model_string: str, tools: Sequence[Callable[..., Any] | BaseTool]
    ) -> tuple[frozenset[str], bool]:
        """(the tools bound from the first request, whether any are left
        for search_tools). Connector tools stay deferred everywhere: four
        connectors were 394k tokens of schemas."""
        core = CORE_TOOL_NAMES
        if keeps_tool_list_fixed(model_string, self._custom_providers):
            connector_names = {tool_name(t) for t in self._extra_tools}
            core = core | {tool_name(t) for t in tools if tool_name(t) not in connector_names}
        defer = self.settings.defer_tools and any(tool_name(t) not in core for t in tools)
        return core, defer

    def resolve_approval(self, request_id: str, approved: bool, scope: str | None = None) -> None:
        # "task": the person allowed this kind of action for the rest of the
        # code task that asked, not only this once.
        code_request = self._code_requests.get(request_id)
        if approved and scope == "task" and code_request is not None:
            self._code_task_allowances.add(code_request)
        future = self._pending_approvals.get(request_id)
        if future is not None and not future.done():
            future.set_result(approved)

    def resolve_question(self, request_id: str, answer: str | list[str | None] | None) -> None:
        future = self._pending_questions.get(request_id)
        if future is not None and not future.done():
            future.set_result(answer)

    def add_steer(self, steer_id: str, text: str) -> None:
        """A note for the turn in progress, read before the model's next
        step. With no turn running (it ended as the note was sent), it is
        sent as a message instead."""
        self._steers.append((steer_id, text))
        if not self._turn_lock.locked():
            asyncio.get_running_loop().create_task(self._send_unread_steers())

    async def _take_steers(self) -> list[str]:
        if not self._steers:
            return []
        steers, self._steers = self._steers, []
        socket = self._live_websocket or self._turn_websocket
        if socket is not None:
            try:
                await socket.send_json({"type": "steers_delivered", "ids": [i for i, _ in steers]})
            except Exception:  # noqa: BLE001 -- the tab went away; the model still has them
                pass
        return [text for _, text in steers]

    def _turn_lock_changed(self, active: bool) -> None:
        BROWSER_HOST.set_active(self.thread_id, active)
        # The turn ended before its next model step could read them.
        if not active and self._steers:
            asyncio.get_running_loop().create_task(self._send_unread_steers())

    async def _send_unread_steers(self) -> None:
        if not self._steers or self._turn_lock.locked():
            return
        steers, self._steers = self._steers, []
        text = "\n\n".join(note for _, note in steers)
        websocket: Any = self._live_websocket
        if websocket is not None:
            try:
                await websocket.send_json(
                    {"type": "steers_requeued", "ids": [i for i, _ in steers], "text": text}
                )
            except Exception:  # noqa: BLE001 -- the tab went away; run unwatched
                websocket = None
        socket: Any = websocket or SilentSocket()
        await self.handle_user_message(text, socket)

    def request_stop(self) -> None:
        """Called directly from ws_endpoint on a "stop" message, not
        awaited -- it has to reach whichever turn is *currently* running,
        same reasoning as resolve_approval. Mostly cooperative: sets a flag
        that _stream_turn/_decide_action_request check at their own natural
        yield points (the turn loop is a single async coroutine rather than a
        worker thread, so a plain flag is enough). Also immediately denies any
        tool call currently blocked on approval, so a stop can't get stuck waiting
        behind an approval prompt no one is going to answer -- the stop-flag checks
        elsewhere
        run between chunks/decisions, which a pending approval wait would
        otherwise never reach. A pending ask_user_question gets the same
        treatment, resolved with a placeholder answer rather than a bool --
        it's a "respond" decision, not approve/reject (see
        _decide_action_request's own docstring).

        Real, user-reported gap in the purely-cooperative design: none of
        the above helps when the turn isn't blocked on an approval/
        question at all, but stuck deep inside a single provider SDK call
        -- e.g. langchain_google_genai's own internal retry/backoff loop on
        a quota error, which can run for the better part of a minute
        without ever yielding a chunk for _stream_turn's stop-flag check to
        run against (see runtime_lg/providers.py's own comment on that same
        bug). Every other agent tool's Stop button reaches for the same
        fix in this situation -- bind directly to cancelling the actual
        in-flight call (AbortController in a JS fetch-based client,
        asyncio.Task.cancel() here) -- so this does too, but *only* when
        there's nothing pending to resolve instead: a pending approval/
        question means the turn is legitimately paused at a LangGraph
        interrupt() waiting on user input, and unblocking it via the
        futures above lets it unwind through its own normal
        Command(resume=...) path, preserving the checkpointer's state
        correctly. Hard-cancelling *that* case instead would skip straight
        past the resume path -- see abandon_orphaned_turn's own docstring,
        which reasons through exactly this for the WebSocket-disconnect
        case and deliberately avoids it there too."""
        self._stop_requested = True
        # The page puts the unread notes back in the composer.
        self._steers.clear()
        self._stop_waited_on_subagents()
        # A browser step can be waiting out a slow page for an hour, in the
        # desktop app where cancelling this turn doesn't reach.
        BROWSER_HOST.cancel(self.thread_id)
        has_pending_interrupt = False
        for request_id, future in list(self._pending_approvals.items()):
            if request_id in self._subagent_request_ids:
                continue
            if not future.done():
                future.set_result(False)
                has_pending_interrupt = True
        for question_future in list(self._pending_questions.values()):
            if not question_future.done():
                question_future.set_result("(Stopped by user before answering.)")
                has_pending_interrupt = True
        if (
            not has_pending_interrupt
            and self._current_turn_task is not None
            and not self._current_turn_task.done()
        ):
            self._current_turn_task.cancel()

    def abandon_orphaned_turn(self, websocket: Any) -> None:
        """Called from app.py's WebSocketDisconnect handler, not
        request_stop -- a real, previously-unhandled deadlock a concurrency
        review caught: _turn_lock (see __init__) means any turn still
        blocked on an approval when its websocket dies would otherwise hang
        onto that lock forever, since nothing can ever resolve a pending
        Future once the socket that would carry its approval_response is
        gone -- silently blocking every future turn on this thread_id too,
        including a genuine reconnect's own resume_after_reconnect trying
        to redeliver that exact same pending approval to a fresh
        connection.

        Deliberately does NOT call request_stop(): that denies the pending
        approval (a real decision, resumed against the checkpointer via
        Command(resume=...)) and would consume the very interrupt a
        reconnect is supposed to redeliver *untouched* -- see
        runtime_lg/README.md's reconnect/restart verdict, the whole reason
        a persistent checkpointer was chosen over InMemorySaver in the
        first place. Hard-cancels whichever task currently holds
        _turn_lock instead: cancellation unwinds that task without ever
        reaching a Command(resume=...) call, so the checkpointer's real
        pending state is left exactly as it was. The lock still gets
        released correctly either way, since `async with` releases on
        cancellation the same as on any other exception.

        Only a turn driven by `websocket`, the connection that went away: a
        background turn (a scheduled run, a run being looked into) only
        shows in whichever tab is open, and must outlive one closing."""
        if self._turn_websocket is not websocket:
            return
        if self._current_turn_task is not None and not self._current_turn_task.done():
            self._current_turn_task.cancel()

    async def switch_model(
        self, model: str, websocket: EventSink, effort: str | None = None
    ) -> None:
        """Change this thread's model, its effort level, or both, from the next request on.
        create_agent() bakes the model into a compiled graph, so the graph is rebuilt around the
        new model object; the same checkpointer and thread keep the history, which is safe even
        mid-approval (the interrupt set comes from tool names and hooks, which a switch does not
        change). A failure (an unknown provider, an SDK that validates eagerly, an unknown effort
        level) leaves everything as it was.

        The custom providers are re-read from disk: the session's copy is a startup snapshot,
        and a provider added in Settings since must be usable without reopening the thread."""
        if ":" not in model:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f'model must be a "provider:model" string, got {model!r}',
                }
            )
            return
        previous = (
            self.model,
            self.lg_agent,
            self._model_string,
            self._effort,
            self._effort_runs_as,
        )
        self._context_window = None
        try:
            if self.settings.providers_config_path is not None:
                self._custom_providers = load_custom_providers(self.settings.providers_config_path)
            effort = effort or self._effort
            new_model, runs_as = self._conversation_model(model, effort)
            lg_tools = self._build_lg_tools(new_model)
            new_lg_agent = self._build_lg_agent(new_model, model, lg_tools)
            self.model, self.lg_agent, self._model_string = new_model, new_lg_agent, model
            self._effort, self._effort_runs_as = effort, runs_as
            await self.send_state(websocket)
        except Exception as exc:  # noqa: BLE001 -- a bad/misconfigured provider must not corrupt session state
            (self.model, self.lg_agent, self._model_string, self._effort, self._effort_runs_as) = (
                previous
            )
            self._context_window = None
            await websocket.send_json(
                {"type": "error", "message": f"Could not switch to {model!r}: {exc}"}
            )

    async def refresh_extra_tools(self, extra_tools: list[Any]) -> None:
        """Rebuild self.lg_agent so this *already-open* thread picks up an
        MCP connector added/removed/version-bumped after this session was
        first created -- real, live-reported bug: __init__ takes a one-time
        snapshot of extra_tools_holder["tools"] (list(extra_tools), see its
        own comment), so before this method existed, connecting a new
        connector only ever affected the *next new* thread_id;
        already-open conversations kept whatever MCP tools existed at
        session-creation time until the process restarted. app.py calls
        this on every currently-open ChatSessionLG right after
        add_mcp_server/remove_mcp_server/bump_mcp_server_version succeeds,
        mirroring switch_model's "rebuild the compiled graph in place, same
        checkpointer/thread_id" shape.

        No websocket parameter, unlike switch_model: this
        runs from a REST endpoint handler, not in response to a message
        from *this* thread's own client, so there is nothing to reply to
        and no previous-state revert to report -- a failure here (e.g. a
        newly-added MCP tool with a schema create_agent rejects) is logged
        and this session's tools are simply left as they were, same
        "don't corrupt a working session" posture as switch_model's own
        except-and-revert branch, just without a websocket to notify.
        Guarded by _turn_lock so this can't race a concurrent
        handle_user_message call on the same session's self.lg_agent/
        self.config, same reasoning as resume_after_reconnect above."""
        async with self._turn_lock:
            self._extra_tools = list(extra_tools)
            try:
                lg_tools = self._build_lg_tools(self.model)
                new_lg_agent = self._build_lg_agent(self.model, self._model_string, lg_tools)
            except Exception:  # noqa: BLE001 -- a bad connector must not corrupt this session
                logger.exception(
                    "refresh_extra_tools: failed to rebuild lg_agent for thread %r, "
                    "keeping its previous tool set",
                    self.thread_id,
                )
                return
            self.lg_agent = new_lg_agent
            self._gated_tool_risks = _risks_of_gated_tools(lg_tools)

    def _build_agent(self) -> Any:
        return build_coordinator_agent(
            self.settings,
            self.thread_id,
            skill_names=self.enabled_skill_names,
            workspace_root=self.workspace_root,
            extra_folders=self.extra_folders,
        )

    @property
    def folders(self) -> list[Path]:
        """The folders this conversation works in, the main one first;
        empty while it uses the app's default workspace."""
        return [self.workspace_root, *self.extra_folders] if self._workspace_explicit else []

    @cached_property
    def _reconfigurer(self) -> SessionReconfigurer:
        return SessionReconfigurer(self)

    def _build_lg_agent_with_risks(self) -> tuple[Any, dict[str, str]]:
        lg_tools = self._build_lg_tools(self.model)
        return (
            self._build_lg_agent(self.model, self._model_string, lg_tools),
            _risks_of_gated_tools(lg_tools),
        )

    async def set_folders(self, paths: list[str], websocket: EventSink) -> bool:
        return await self._reconfigurer.set_folders(paths, websocket)

    async def add_folder(self, path: str, websocket: EventSink) -> bool:
        return await self._reconfigurer.add_folder(path, websocket)

    async def set_enabled_skills(
        self, skill_names: set[str], websocket: EventSink, *, announce: bool = True
    ) -> None:
        await self._reconfigurer.set_enabled_skills(skill_names, websocket, announce=announce)

    async def send_state(self, websocket: EventSink, *, on_connect: bool = False) -> None:
        if self._context_window is None:
            self._context_window = await asyncio.to_thread(
                self._context_window_client.get_context_window, self._model_string
            )
        state: dict[str, Any] = {
            "type": "state",
            "plan_mode": self.plan_mode,
            "accept_edits": self.accept_edits,
            "auto_mode": self.auto_mode,
            "model": self._model_string,
            "effort": self._effort,
            "effort_runs_as": self._effort_runs_as,
            "context_window": self._context_window,
            "enabled_skills": sorted(self.enabled_skill_names),
            "workspace_root": str(self.workspace_root),
            "workspace_explicit": self._workspace_explicit,
            "folders": [str(folder) for folder in self.folders],
            "connector_tools": sorted(
                tool_name(t)
                for t in self._extra_tools
                if (get_tool_metadata(cast(Any, t)).category or "").startswith("mcp:")
            ),
        }
        if on_connect:
            # A tab opening mid-turn (most often: a scheduled run executing
            # in the background) needs to show that turn as running, with
            # Stop available. Connect-time only: a state sent from *inside*
            # a turn (/plan, a model switch) holds the lock itself.
            state["turn_in_flight"] = self._turn_lock.locked()
        await websocket.send_json(state)

    def workspace_scope(self) -> WorkspaceScope:
        return WorkspaceScope(
            self.workspace_root,
            extra_readable=[*self.settings.extra_readable_dirs, *self.extra_folders],
            extra_writable=[*self.settings.extra_writable_dirs, *self.extra_folders],
        )

    def workflow_context(self, model: str | None) -> StepContext:
        return self._drafting.workflow_context(model)

    async def draft_workflow(self, name_hint: str = "") -> WorkflowDraft:
        return await self._drafting.draft_workflow(name_hint)

    @property
    def checkpointer(self) -> Any:
        return self._checkpointer

    def is_workflow_run(self) -> bool:
        """This thread's checkpoints belong to a workflow's graph, not this
        session's agent -- driving the agent on them (resuming a pending
        interrupt, a new turn) would feed one graph's state to another."""
        parsed = parse_run_thread_id(self.thread_id)
        if parsed is None:
            return False
        trigger = ScheduledTriggerStore(self.settings.state_dir).load(parsed[0])
        return trigger is not None and trigger.workflow is not None

    async def get_activity(self) -> dict[str, Any]:
        catalog = {
            tool_name(t): get_tool_metadata(cast(Any, t))
            for t in [*self._base_tools, *self._extra_tools]
        }
        parsed = parse_run_thread_id(self.thread_id)
        if parsed is not None:
            trigger = ScheduledTriggerStore(self.settings.state_dir).load(parsed[0])
            run = trigger.find_run(parsed[1]) if trigger is not None else None
            if trigger is not None and trigger.workflow is not None and run is not None:
                return summarize_workflow_run(
                    trigger.workflow, run, catalog, self.workspace_scope()
                )
        state = await self.lg_agent.aget_state(self.config)
        messages = list(state.values.get("messages", [])) if state.values else []
        return summarize_activity(messages, catalog, self.workspace_scope())

    async def get_context_breakdown(self) -> dict[str, Any]:
        """Where this thread's context-window budget actually goes --
        backs the context-usage panel (ContextRing.tsx's expanded view).
        See context_usage.py's own module docstring for the measurement
        approach and its documented approximation.

        Recomputes the currently-enabled skills' own listing text fresh
        (rather than trying to re-extract it from the already-concatenated
        self._instructions) via the exact same load-then-filter-by-name
        expression __init__/set_enabled_skills/switch_model already use
        to build self._instructions in the first place -- guaranteed to
        match, since self.enabled_skill_names is the one shared input
        every one of those call sites feeds into build_coordinator_agent's
        own identical filter."""
        if self._context_window is None:
            self._context_window = await asyncio.to_thread(
                self._context_window_client.get_context_window, self._model_string
            )
        skills = [
            skill
            for skill in load_builtin_skills() + load_skills(self.settings.skills_dir)
            if skill.name in self.enabled_skill_names
        ]
        skills_listing = format_skill_listing(skills) if skills else ""
        last_total = (
            self._last_usage_metadata["total_tokens"] if self._last_usage_metadata else None
        )
        base_tools = list(self._base_tools)
        mcp_tools = list(self._extra_tools)
        core_names, defer = self._tool_binding(self._model_string, [*base_tools, *mcp_tools])
        if defer:
            # Only what a request sends counts; the rest waits behind
            # search_tools.
            bound = bound_tool_names(core_names)
            deferred = [t for t in [*base_tools, *mcp_tools] if tool_name(t) not in bound]
            base_tools = [t for t in base_tools if tool_name(t) in bound]
            base_tools.extend([build_search_tools_tool(deferred), build_use_tool_tool()])
            mcp_tools = [t for t in mcp_tools if tool_name(t) in bound]
        return await asyncio.to_thread(
            build_context_breakdown,
            instructions=build_instructions(self._instructions, defer_tools=defer),
            skills_listing=skills_listing,
            base_tools=base_tools,
            mcp_tools=mcp_tools,
            context_window=self._context_window or 0,
            auto_compact_threshold=self.settings.auto_compact_threshold,
            last_total_tokens=last_total,
        )

    async def notify_resync(self) -> None:
        """Tell whichever browser tab is currently watching this thread
        (if any) that something changed server-side outside of its own
        turn -- a background wake/scheduled-task/sub-agent resuming this
        thread while nobody was actively typing into it. Real, previously-
        documented gap this closes: a poller-triggered resume wrote
        correctly to the checkpointer but never appeared in an already-
        open tab until its next reload/reconnect (ROADMAP.md).

        Deliberately just re-sends the exact same "history" event
        send_history already sends on every fresh connection, rather than
        inventing a new WS message type/frontend handler -- the frontend's
        "history" reducer case already replaces state.items wholesale
        with the authoritative replay (see reducer.ts), which is exactly
        "go re-fetch the now-correct state," and reusing it means zero
        new frontend wiring. This is the "stored state + resync" shape
        this feature's own design discussion found Claude Code's own
        Remote Control (stored transcript, reconnect/resync) and
        claude-code-best's goal service (plain status flag, no event
        emitter) both already use, rather than a full multi-listener
        broadcast bus -- this app only ever has one browser tab watching
        a given thread at a time in practice, so there's nothing more to
        fan out to.

        Silently does nothing if no tab is currently connected (the
        common case for an unattended wake) -- there's nothing to nudge.
        Best-effort: a dead/closing socket's send can raise, and a missed
        resync is recoverable (the next reconnect sees correct state
        anyway), not worth failing whatever background work triggered
        this over."""
        websocket = self._live_websocket
        if websocket is None:
            return
        try:
            await self.send_history(websocket)
        except Exception:
            logger.debug("notify_resync: failed to notify the live tab for %s", self.thread_id)

    @cached_property
    def _history(self) -> ConversationHistory:
        return ConversationHistory(self)

    async def send_history(self, websocket: EventSink) -> None:
        await self._history.send_history(websocket)

    async def load_older_messages(self, websocket: EventSink) -> None:
        await self._history.load_older_messages(websocket)

    async def _stream_turn(self, turn_input: Any, websocket: EventSink) -> str:
        """Runs one astream() call, forwarding the model's own narration as
        "agent_delta" events and each tool's return value as "tool_result",
        same wire shape as ChatSession's _on_delta/_post_tool_use. Returns
        only the *last* model response's own narration text -- not every
        response of this call concatenated -- reset (text_parts.clear())
        at each ToolMessage boundary, the same point _capture_segment_usage
        already resets `segment` at. A single astream() call can cover more
        than one model response when it includes an *ungated* tool call
        (the loop just keeps going past the ToolMessage); without the reset,
        this method's return value would glue the pre-tool narration onto
        the post-tool one with no separator, even though the pre-tool text
        already streamed live as its own "agent_delta" bubble.

        The gated case has the identical join done differently: this method's
        own astream() loop ends *without* a ToolMessage the moment the model
        proposes a call that needs approval (the interrupt fires first), so
        its return value here is already just the pre-tool narration, single-
        segment; the risk there is a *caller* joining this call's return
        value with a later _resolve_pending_approvals one -- see that
        method's own docstring for the matching half of this fix.

        Also recovers each tool call's arguments for the PostToolUse hook
        payload below -- a ToolMessage only carries a tool's result, not the
        arguments it was called with, so this accumulates the preceding
        AIMessageChunk stream (stream_mode=["messages"] yields incremental
        deltas, merged here via AIMessageChunk's own __add__) into a full
        AIMessage and reads its .tool_calls. Flushed into
        self._pending_tool_args in two places: right before a ToolMessage
        that arrived in the *same* call (the common, non-gated-tool case),
        and again unconditionally once the astream loop ends (the
        approval-gated case -- the AIMessage proposing a gated call is
        always fully streamed *before* the interrupt fires, since
        interrupt() runs in after_model once the AIMessage already exists,
        but the interrupt then ends this call's astream loop with no
        ToolMessage ever arriving in it; the flush at the end is what
        carries those args over to the *next* _stream_turn call --
        _resolve_pending_approvals's post-resume one -- where the
        ToolMessage for that call actually shows up). registered_ids
        prevents the shared end-of-loop flush from double-registering a
        call already flushed by the inline branch above it.

        Checks self._stop_requested after every chunk (see request_stop's
        docstring) -- cooperative, so it can't interrupt a single model
        call already in flight (same limitation the old runtime's
        stop_event has for any non-token-streaming provider), but it stops
        consuming *further* chunks/turns promptly. Explicitly closes the
        astream() generator on the way out (in a finally, whether the loop
        ended naturally or via a stop-triggered break) rather than just
        letting it fall out of scope -- an abandoned, ungarbage-collected
        async generator keeps running in the background instead of
        propagating GeneratorExit into LangGraph's own execution.

        Also tracks `self._last_usage_metadata`: a *separate* accumulator
        (`segment`, distinct from `accumulated` above) that resets at each
        ToolMessage boundary, so it only ever sums the chunks of the single
        most recent model response -- not the whole multi-response turn,
        which would double-count (each individual response's own
        usage_metadata.total_tokens already reflects the *cumulative*
        context size at that point, since Gemini/Anthropic/OpenAI all
        report "tokens in the whole prompt this call sent" as input_tokens,
        not just what's new since the last call). Verified live against
        real Gemini through this exact astream(stream_mode=["messages"])
        path, including a real tool call in between two model responses --
        confirmed each individual response's accumulated usage_metadata is
        correct (not the all-zero result an earlier, older
        langchain-google-genai version returned, see runtime_lg/README.md's
        "usage bar" section for the fix and how the earlier finding was
        superseded by an upstream fix in that package). Left as None (no
        WS event sent) if a response never populates usage_metadata at all
        -- some providers/configurations still don't; see that same
        section for langchain-openai's stream_usage caveat.

        _capture_segment_usage also sends a live "usage" WS event itself,
        at every boundary it runs at (each ToolMessage, plus once more at
        this method's own return) -- not only from the two post-turn sends
        the callers below already do once _stream_turn returns. Drives the
        composer's live running-token counter (ContextRing gets the same
        event) across a long, multi-tool-call turn instead of only
        updating once the whole turn is over."""
        agent = self.lg_agent
        config = self.config
        self._turn_websocket = websocket
        if not isinstance(turn_input, Command):
            await _close_orphaned_tool_calls(agent, config)
        text_parts: list[str] = []
        accumulated: AIMessageChunk | None = None
        segment: AIMessageChunk | None = None
        registered_ids: set[str] = set()

        def _flush_accumulated() -> None:
            nonlocal accumulated
            if accumulated is None:
                return
            for call in accumulated.tool_calls:
                call_id = call["id"]
                if call_id is not None and call_id not in registered_ids:
                    # The stream carries the model's own use_tool call; the
                    # tool's result comes back under the real name.
                    name, args = unwrap_use_tool_call(call["name"], call["args"])
                    self._pending_tool_args[name].append(args)
                    registered_ids.add(call_id)
            # Providers number each response's tool calls from index 0 and
            # send a call's later argument pieces without its id; adding
            # chunks joins such a piece to the first call with that index.
            # Carried into the next response, its pieces would join this
            # response's call and the new call would lose its arguments.
            accumulated = None

        async def _capture_segment_usage() -> None:
            nonlocal segment
            if segment is not None and segment.usage_metadata:
                self._last_usage_metadata = segment.usage_metadata
                # Live, not just at turn-end: a multi-step turn (tool call,
                # then another model response) previously only told the
                # frontend the token count once the *whole* turn finished
                # (see the callers' own "usage" sends after _stream_turn
                # returns) -- nothing to drive a live-updating counter with
                # while a long turn is still running. Each individual
                # response's usage_metadata.total_tokens is already the
                # cumulative context size at that point (see this method's
                # own docstring), so sending it here, at every boundary this
                # function already runs at, is a correct running total, not
                # an approximation.
                await websocket.send_json(usage_event(segment.usage_metadata))
            segment = None

        # "updates" is only for the model node's finished message: it lands
        # before any of its tool calls run, which "messages" has no event for.
        stream = agent.astream(turn_input, config=config, stream_mode=["messages", "updates"])
        try:
            async for mode, chunk in stream:
                if mode == "updates":
                    await self._announce_started_tools(chunk, websocket)
                    continue
                message, _metadata = chunk
                if isinstance(message, AIMessageChunk):
                    text = _extract_text(message.content)
                    if text:
                        text_parts.append(text)
                        await websocket.send_json({"type": "agent_delta", "text": text})
                    accumulated = message if accumulated is None else accumulated + message
                    segment = message if segment is None else segment + message
                elif isinstance(message, ToolMessage):
                    _flush_accumulated()
                    await _capture_segment_usage()
                    # A tool call (gated or not) ends the model's current
                    # response -- discard whatever narration text_parts
                    # accumulated for it, same boundary _capture_segment_usage
                    # already resets `segment` at. That narration already
                    # streamed live as its own "agent_delta" bubble; without
                    # this reset, this call's eventual return value would glue
                    # it onto whatever the model says *after* the tool result
                    # comes back, with no separator -- a real bug found live
                    # (see this method's own docstring).
                    text_parts.clear()
                    name = message.name or ""
                    result_value = _tool_result_value(message.content)
                    args = (
                        self._pending_tool_args[name].pop(0)
                        if self._pending_tool_args[name]
                        else {}
                    )
                    await self._run_post_tool_use_hooks(name, args, result_value)
                    # ask_user_question's own "question"/"answered" card (sent by
                    # _decide_question_request as question_required, resolved locally
                    # on answer -- see reducer.ts's "question_required"/
                    # "local_question_answered" cases) already fully represents this
                    # call; sending the normal tool_result here too would additionally
                    # fall into the reducer's tool_result fallback branch (no matching
                    # pending "tool" item exists, since question tools never got a
                    # "tool_call" one) and add a second, redundant "Asked: ..." row
                    # underneath the card for the same interaction.
                    if name not in QUESTION_TOOL_NAMES and name not in TASK_DRAFT_TOOL_NAMES:
                        # `args` (recovered above, same value the hook just got)
                        # rides along so a live turn's collapsed row can show the
                        # real filename/query -- without this the frontend only
                        # ever learns the actual arguments for a *gated* tool
                        # (via approval_required) or a *replayed* one (via
                        # history's own checkpointed entry.arguments); an
                        # ungated tool completing in a live turn had no event
                        # carrying arguments at all until now, so its row always
                        # fell back to generic phrasing ("Read a file" instead
                        # of "Read notes.txt").
                        await websocket.send_json(
                            {
                                "type": "tool_result",
                                "tool_name": name,
                                "arguments": args,
                                "result": result_value,
                                "is_error": message.status == "error",
                            }
                        )
                elif isinstance(message, AIMessage):
                    # Real, live-caught gap: a middleware-injected terminal
                    # message (e.g. ModelCallLimitMiddleware's
                    # exit_behavior="end" AIMessage, added directly via a
                    # before_model hook's return dict rather than an actual
                    # model call) never goes through _generate/_stream, so
                    # stream_mode=["messages"] emits it as one complete
                    # AIMessage instead of the usual AIMessageChunk deltas
                    # -- the `isinstance(message, AIMessageChunk)` branch
                    # above never matches it (AIMessageChunk is a subclass
                    # of AIMessage, not the reverse), so without this branch
                    # its content was silently dropped and the turn ended
                    # with an empty "[no reply -- ...]" instead of telling
                    # the user *why* it stopped. Confirmed live: printing
                    # the raw astream(stream_mode=["messages"]) output for a
                    # max_turns-capped run shows this exact message arriving
                    # as a plain AIMessage, not a chunk.
                    text = _extract_text(message.content)
                    if text:
                        text_parts.append(text)
                        await websocket.send_json({"type": "agent_delta", "text": text})
                if self._stop_requested:
                    break
        finally:
            await stream.aclose()
        _flush_accumulated()
        await _capture_segment_usage()
        return "".join(text_parts)

    async def _announce_started_tools(self, update: Any, websocket: EventSink) -> None:
        """Tells the page which ungated calls are about to run, so it can
        show them running. Gated ones are announced by the approval path
        instead, and only when nobody is asked: a call waiting for approval
        shows as its approval card."""
        if not isinstance(update, dict):
            return
        for node_update in update.values():
            if not isinstance(node_update, dict):
                continue
            for message in node_update.get("messages", []) or []:
                if not isinstance(message, AIMessage):
                    continue
                for call in message.tool_calls:
                    if call["name"] not in self._gated_tool_risks:
                        await self._send_tool_started(call["name"], call["args"], websocket)

    async def _send_tool_started(
        self, name: str, args: dict[str, Any], websocket: EventSink
    ) -> None:
        if name in QUESTION_TOOL_NAMES or name in TASK_DRAFT_TOOL_NAMES:
            return
        await websocket.send_json({"type": "tool_started", "tool_name": name, "arguments": args})

    async def _run_pre_tool_use_hooks(self, name: str, args: dict[str, Any]) -> str | None:
        return await tool_hooks.run_pre_tool_use(self.hooks_config, name, args)

    async def _run_post_tool_use_hooks(self, name: str, args: dict[str, Any], result: Any) -> None:
        await tool_hooks.run_post_tool_use(self.hooks_config, name, args, result)

    async def _run_observational_hooks(self, event: str, payload: dict[str, Any]) -> None:
        await tool_hooks.run_observational(self.hooks_config, event, payload)

    async def run_interrupt_hooks(self) -> None:
        await self._run_observational_hooks(
            "Interrupt", {"event": "Interrupt", "thread_id": self.thread_id}
        )

    async def run_session_end_hooks(self) -> None:
        await self._run_observational_hooks(
            "SessionEnd", {"event": "SessionEnd", "thread_id": self.thread_id}
        )

    async def _build_document_edit_preview(
        self, tool_name_: str, args: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        return await build_document_edit_preview(
            tool_name_,
            args,
            self.workspace_root,
            self.settings.extra_readable_dirs,
            self.settings.extra_writable_dirs,
            Path(self.settings.state_dir),
        )

    async def _decide_action_request(
        self, request: dict[str, Any], websocket: Any, *, honor_stop: bool = True
    ) -> Any:
        return await self._approvals._decide_action_request(
            request, websocket, honor_stop=honor_stop
        )

    def _effective_run_approval_mode(self) -> str | None:
        return self._approvals._effective_run_approval_mode()

    def _code_allows(self, name: str, websocket: Any) -> bool:
        return self._approvals._code_allows(name, websocket)

    def _auto_approves(self, name: str) -> AutoApproveReason | None:
        return self._approvals._auto_approves(name)

    def _toggle_mode(self, mode: str) -> None:
        """Plan, Accept Edits and Auto are one mode at a time; none of them is
        Manual. Toggling the current one returns to Manual."""
        turning_on = not {
            "plan": self.plan_mode,
            "accept-edits": self.accept_edits,
            "auto": self.auto_mode,
        }[mode]
        self.plan_mode = turning_on and mode == "plan"
        self.accept_edits = turning_on and mode == "accept-edits"
        self.auto_mode = turning_on and mode == "auto"
        if self.auto_mode:
            self._auto_blocks_in_row = 0
            self._auto_paused = False

    def _auto_review_active(self) -> bool:
        return self._approvals._auto_review_active()

    async def _auto_review(
        self, name: str, args: dict[str, Any], *, delegated_task: str = ""
    ) -> Verdict | None:
        return await self._approvals._auto_review(name, args, delegated_task=delegated_task)

    def _auto_approval_active(self) -> bool:
        return self._approvals._auto_approval_active()

    @cached_property
    def _approvals(self) -> ApprovalDecider:
        return ApprovalDecider(self)

    def _load_exec_policy(self) -> ExecPolicy:
        return load_exec_policy(self.settings.exec_policy_path)

    def _decidable_unattended(self, request: dict[str, Any]) -> bool:
        """Whether _decide_action_request can settle this request with
        nobody present other than by refusing for lack of a person. A gated
        call that can't must stay parked for someone to approve later,
        rather than be rejected and let the run carry on without it."""
        name = request["name"]
        if name in QUESTION_TOOL_NAMES or name in TASK_DRAFT_TOOL_NAMES:
            return True
        if name not in self._gated_tool_risks or self.plan_mode:
            return True
        if self._auto_approves(name) is not None:
            return True
        if self._auto_review_active():
            return True
        if name in EXEC_POLICY_TOOL_NAMES:
            decision, _ = self._load_exec_policy().decide(request["args"].get("script", ""))
            return decision != "prompt"
        return False

    async def _decide_question_request(
        self, args: dict[str, Any], websocket: EventSink
    ) -> dict[str, Any]:
        return await self._approvals._decide_question_request(args, websocket)

    async def _decide_plan_request(
        self, args: dict[str, Any], websocket: EventSink
    ) -> dict[str, Any]:
        return await self._approvals._decide_plan_request(args, websocket)

    async def _decide_task_draft_request(
        self, name: str, args: dict[str, Any], websocket: EventSink
    ) -> dict[str, Any]:
        return await self._approvals._decide_task_draft_request(name, args, websocket)

    async def _resolve_pending_approvals(self, websocket: EventSink) -> str | None:
        """While the graph is paused, decide every pending action request
        and resume -- looping in case a resumed turn immediately hits
        another approval-gated call.

        Returns the *last* resumed `_stream_turn` call's own text, not a
        concatenation of every round -- each round already streamed its own
        narration live as its own "agent_delta" bubble (see reducer.ts's
        agent_delta/agent_message cases), so re-joining them here would
        duplicate that text in the final "agent_message" a caller sends
        with this return value: a real bug found live (DeepSeek/GLM, both
        of which narrate before a gated tool call, unlike this app's usual
        Gemini/Anthropic testing) -- "I'll create notes.txt...Done! I
        created **notes.txt**..." glued with no separator, because the
        pre-tool narration and the post-tool narration were joined as if
        they were one continuous reply. Returns None specifically (not
        "") when the loop never runs at all (nothing was pending) -- a
        caller needs to tell "nothing to resolve, keep whatever text you
        already had" apart from "resolved, and the model said nothing
        further," which an empty string can't distinguish on its own.

        More than one *task* can be pending at once -- concretely, two
        concurrent spawn_agent calls proposed in the same AIMessage, each
        independently bridging its own child's approval via interrupt()
        (see runtime_lg/subagents.py). LangGraph gives each task's
        interrupt its own id and, once more than one is pending
        simultaneously, *requires* resuming each individually via
        `Command(resume={interrupt_id: value, ...})` -- a single shared
        resume value (this method's own approach before this was found and
        fixed) raises `RuntimeError: When there are multiple pending
        interrupts, you must specify the interrupt id when resuming` the
        moment a second task is pending at the same time as the first.
        Live-verified against real Gemini: two concurrent spawn_agent
        calls, one approved and one rejected, resolved correctly and
        independently, with no cross-contamination between them -- see
        runtime_lg/README.md.

        Multiple pending tasks are decided *sequentially* here (one
        `_decide_action_request` await fully completes before the next
        task's own interrupt is even inspected) -- so a caller/client must
        answer the first approval_required before the second one is sent,
        not expect both up front. A test (or a future UI) that tries to
        `receive` two approval_required messages back-to-back before
        answering either one will deadlock against this method, not
        against LangGraph -- see test_concurrent_spawn_agent_approvals_
        resolve_independently's request/respond/request/respond shape."""
        agent = self.lg_agent
        config = self.config
        latest_text: str | None = None
        state = await agent.aget_state(config)
        while state.next:
            if not can_resolve_approvals(websocket) and not all(
                self._decidable_unattended(request)
                for task in state.tasks
                for interrupt in task.interrupts
                for request in interrupt.value.get("action_requests", [])
            ):
                break
            resume_map: dict[str, Any] = {}
            for task in state.tasks:
                for interrupt in task.interrupts:
                    action_requests = interrupt.value.get("action_requests", [])
                    decisions = [
                        await self._decide_action_request(request, websocket)
                        for request in action_requests
                    ]
                    resume_map[interrupt.id] = {"decisions": decisions}

            latest_text = await self._stream_turn(Command(resume=resume_map), websocket)
            state = await agent.aget_state(config)
        return latest_text

    async def resume_after_reconnect(self, websocket: EventSink) -> None:
        """If this session's graph is still paused on an approval from
        before a dropped connection or a process restart, redeliver it now
        instead of leaving the browser with nothing to resolve -- the
        checkpointer already durably persisted the pending state (that's
        the whole point of a persistent checkpointer over InMemorySaver, see
        runtime_lg/README.md's reconnect/restart verdict); this just
        re-runs the same delivery path a fresh turn's approval already
        uses. A no-op when nothing is pending.

        Guarded by _turn_lock, same reasoning as handle_user_message -- this
        runs as a backgrounded task right after connect (see ws_endpoint),
        so without the lock it could run fully concurrently with a
        user_message the client sends immediately after connecting, racing
        on the same self.lg_agent/self.config the way two concurrent
        handle_user_message calls would."""
        if self.is_workflow_run():
            return
        async with self._turn_lock:
            self._current_turn_task = asyncio.current_task()
            # So that this connection closing releases the lock too:
            # abandon_orphaned_turn only cancels a turn driven by the socket
            # that went away, and a question redelivered here waits on it.
            self._turn_websocket = websocket
            # A turn hard-cancelled mid-tool also leaves state.next set, but
            # with no interrupt to redeliver -- resuming it would silently
            # re-run that tool (possibly minutes of work the user just
            # stopped), so close it off instead.
            await _close_orphaned_tool_calls(self.lg_agent, self.config)
            state = await self.lg_agent.aget_state(self.config)
            if not state.next:
                return
            # state.next already confirmed truthy above, so
            # _resolve_pending_approvals's own while loop is guaranteed to
            # run at least once -- its None return (nothing was pending)
            # can't actually happen here; `or ""` only satisfies the type
            # checker, not a real runtime fallback.
            text = await self._resolve_pending_approvals(websocket) or ""
            await self._record_resumed_run_status()
            await websocket.send_json({"type": "agent_message", "text": format_reply(text)})
            if self._last_usage_metadata is not None:
                await websocket.send_json(usage_event(self._last_usage_metadata))
            await websocket.send_json({"type": "tasks_changed"})

    def offer_pending_approval_to_live_tab(self) -> None:
        """A background run that parked on an approval while someone was
        watching: hand the approval to that tab now, the same way a fresh
        connection would get it, instead of waiting for a reload."""
        websocket = self._live_websocket
        if websocket is None:
            return
        self._offer_task = asyncio.create_task(self.resume_after_reconnect(websocket))

    async def _record_resumed_run_status(self) -> None:
        """A scheduled run that parked on an approval ended as
        "needs_approval"; once someone resolves it here and the turn
        finishes, the run record should say how it actually ended."""
        parsed = parse_run_thread_id(self.thread_id)
        if parsed is None:
            return
        trigger_id, run_id = parsed
        store = ScheduledTriggerStore(self.settings.state_dir)
        trigger = store.load(trigger_id)
        run = trigger.find_run(run_id) if trigger is not None else None
        if run is None or run.status != "needs_approval":
            return
        state = await self.lg_agent.aget_state(self.config)
        if any(task.interrupts for task in state.tasks):
            return
        store.finish_run(trigger_id, run_id, "stopped" if self._stop_requested else "completed")

    async def _handle_compact(self, websocket: EventSink) -> None:
        await self._history._handle_compact(websocket)

    async def _handle_clear(self, websocket: EventSink) -> None:
        await self._history._handle_clear(websocket)

    async def _current_messages(self) -> list[Any]:
        return await self._history._current_messages()

    async def handle_edit_message(
        self,
        index: int,
        text: str,
        websocket: EventSink,
        images: list[str] | None = None,
    ) -> None:
        await self._history.handle_edit_message(index, text, websocket, images=images)

    async def handle_rewind_message(self, index: int, websocket: EventSink) -> None:
        await self._history.handle_rewind_message(index, websocket)

    @cached_property
    def _skill_save(self) -> SkillSave:
        return SkillSave(self)

    async def _handle_save_skill(self, name: str, websocket: EventSink) -> None:
        await self._skill_save._handle_save_skill(name, websocket)

    async def _handle_pending_skill_save_proposal(self, text: str, websocket: EventSink) -> None:
        await self._skill_save._handle_pending_skill_save_proposal(text, websocket)

    async def handle_user_message(
        self,
        text: str,
        websocket: EventSink,
        images: list[str] | None = None,
    ) -> None:
        # See _turn_lock's docstring in __init__: this serializes turns so a
        # message sent while one is still running waits its turn instead of
        # racing it.
        if self.is_workflow_run():
            await websocket.send_json(
                {"type": "error", "message": "A workflow run doesn't take messages."}
            )
            return
        meta = ThreadMetaStore(self.settings.state_dir)
        if meta.get(self.thread_id)["archived"]:
            # Talking to an archived conversation brings it back.
            meta.update(self.thread_id, archived=False)
        try:
            async with self._turn_lock:
                self._current_turn_task = asyncio.current_task()
                self._report_turns_in_row = 0
                self.turn_running = True
                await self._handle_user_message_locked(text, websocket, images=images)
        finally:
            self.turn_running = False
            # Worth a look in the sidebar unless someone had the
            # conversation open when it ended (a stop counts as ended).
            ThreadMetaStore(self.settings.state_dir).mark_finished(
                self.thread_id, watched=self._live_websocket is not None
            )
            # Messages that came in during the turn, or waited on the cap.
            self.schedule_inbox_delivery()

    async def _handle_user_message_locked(
        self,
        text: str,
        websocket: EventSink,
        images: list[str] | None = None,
        *,
        notice: bool = False,
    ) -> None:
        await self._run_observational_hooks(
            "UserPromptSubmit",
            {"event": "UserPromptSubmit", "thread_id": self.thread_id, "text": text},
        )
        # Skills are switched on and off globally in Settings; a conversation
        # that's already open picks the change up at its next turn.
        wanted_skills = enabled_skill_names(self.settings.skills_dir, self.settings.state_dir)
        if wanted_skills != self.enabled_skill_names:
            await self.set_enabled_skills(wanted_skills, websocket, announce=False)
        # A notice isn't the user's reply to anything, nor a command.
        stripped_lower = "" if notice else text.strip().lower()

        if self.pending_save_skill_proposal is not None and not notice:
            await self._handle_pending_skill_save_proposal(text, websocket)
            return

        if stripped_lower in ("/plan", "/accept-edits", "/auto"):
            self._toggle_mode(stripped_lower[1:])
            await self.send_state(websocket)
            return

        if stripped_lower == "/compact":
            await self._handle_compact(websocket)
            return

        if stripped_lower == "/clear":
            await self._handle_clear(websocket)
            return

        command, _, rest = text.strip().partition(" ")
        command_lower = command.lower()

        if command_lower == "/saveskill":
            await self._handle_save_skill(rest.strip(), websocket)
            return

        user_input = text
        if stripped_lower.startswith("/"):
            name = command[1:].lower()
            if name == "init":
                user_input = INIT_PROMPT
            elif name == "saveworkflow":
                if not rest.strip():
                    await websocket.send_json(
                        {"type": "error", "message": "Usage: /saveworkflow <name>"}
                    )
                    return
                user_input = SAVE_WORKFLOW_PROMPT.format(name=rest.strip())
            elif name in self.skills_by_slug:
                skill = self.skills_by_slug[name]
                fallback = (
                    "(no additional request given -- follow the skill and "
                    "proceed, or ask what is needed.)"
                )
                user_input = (
                    f"[Skill '{skill.name}' invoked directly via /{name} -- "
                    f"follow its instructions below for this request.]\n\n"
                    f"{skill.body}\n\n---\nUser request: {rest.strip() or fallback}"
                )
            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown command: {command}. Type a skill name or /init.",
                    }
                )
                return

        if self.plan_mode:
            mode_note = PLAN_MODE_NOTE
        elif self.accept_edits:
            mode_note = ACCEPT_EDITS_MODE_NOTE
        elif self.auto_mode:
            mode_note = AUTO_MODE_NOTE
        else:
            mode_note = NORMAL_MODE_NOTE
        # current_date_note() lives here, not in the system prompt --
        # see its own docstring in runtime_lg/messages.py for why that
        # matters for caching across every provider, not just Anthropic.
        context = conversation_context(self.settings, self.workspace_root, self.extra_folders)
        state = await self.lg_agent.aget_state(self.config)
        history = list(state.values.get("messages", [])) if state.values else []
        told = last_conversation_context(history) == context
        model_input = (
            current_date_note()
            + mode_note
            + language_note(text)
            + ("" if told else context_note(context))
            + user_input
        )

        content: str | list[dict[str, Any]] = model_input
        if images:
            content = [{"type": "text", "text": model_input}]
            content.extend({"type": "image_url", "image_url": {"url": url}} for url in images)
        turn_input = {"messages": [{"role": "user", "content": content}]}

        # Reset for this turn -- see _stream_turn's docstring. A stale
        # entry from a previous turn popping for the wrong call is the only
        # real risk of *not* resetting; there's no other state to preserve
        # across turns here.
        self._pending_tool_args = defaultdict(list)
        # Fresh start for /stop each turn: a stop requested during a previous turn (or
        # left over from one that already finished) must not immediately
        # halt this new one.
        self._stop_requested = False
        if not history and self._wants_title():
            self._title_task = asyncio.create_task(self._name_thread(websocket, text))

        retried_after_grpc_metadata_overflow = False
        reply_text = ""  # narrowing hint only -- always reassigned before use, see the loop below
        while True:
            try:
                # reply_text ends up as just the *last* model response's own
                # text, not every response of this turn concatenated -- see
                # _resolve_pending_approvals's docstring for why joining them
                # was a real bug (duplicated, glued-together narration on any
                # model that talks before a gated tool call). Overwritten
                # below only if approvals actually resolved something; None
                # means nothing was pending, so the initial call's own text
                # already *is* the whole (single-segment) reply.
                reply_text = await self._stream_turn(turn_input, websocket)
                # Unattended, only worth entering when something can
                # approve without a person; _resolve_pending_approvals
                # itself leaves anything else parked.
                if can_resolve_approvals(websocket) or self._auto_approval_active():
                    resolved_text = await self._resolve_pending_approvals(websocket)
                    if resolved_text is not None:
                        reply_text = resolved_text
                break
            except asyncio.CancelledError:
                # request_stop() hard-cancels this task (see its own
                # docstring) whenever there's no pending approval/question to
                # resolve instead -- exactly the case where _stream_turn is
                # stuck inside a raw provider call with no chunk ever yielded
                # for its cooperative stop-flag check to run against. No
                # partial reply_text exists at this point (the cancellation
                # interrupts _stream_turn before it can return one), so this
                # sends just the marker -- same "agent_message" type and
                # "[stopped]" convention the cooperative-stop path below
                # already uses, so the frontend needs no changes to render it.
                try:
                    await websocket.send_json({"type": "agent_message", "text": "[stopped]"})
                    # The task panel refreshes on this, as after any other turn.
                    await websocket.send_json({"type": "tasks_changed"})
                except Exception:  # noqa: BLE001 -- the client is already gone
                    pass
                return
            except Exception as exc:  # noqa: BLE001 -- surface any provider/tool error to the client
                is_grpc_metadata_overflow = _GRPC_METADATA_OVERFLOW_SIGNATURE in str(exc)
                if not retried_after_grpc_metadata_overflow and is_grpc_metadata_overflow:
                    retried_after_grpc_metadata_overflow = True
                    try:
                        self.model, self._effort_runs_as = self._conversation_model(
                            self._model_string, self._effort
                        )
                        lg_tools = self._build_lg_tools(self.model)
                        self.lg_agent = self._build_lg_agent(
                            self.model, self._model_string, lg_tools
                        )
                    except Exception:  # noqa: BLE001 -- rebuild failure falls through to the original error below
                        pass
                    else:
                        continue
                try:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                except Exception:  # noqa: BLE001 -- the client is already gone
                    # Live-hit: a client that drops mid-turn (network blip,
                    # tab closed) makes _stream_turn's own websocket.send_json
                    # raise WebSocketDisconnect, landing here -- but the
                    # socket is already closed by then, so THIS send fails
                    # too (Starlette raises RuntimeError('Cannot call "send"
                    # once a close message has been sent.') once it's
                    # recorded the close). Left uncaught, that second
                    # exception propagated out of handle_user_message, which
                    # ws_endpoint fires via asyncio.create_task with nothing
                    # ever awaiting/checking its result -- so it surfaced
                    # only as an alarming "asyncio: Task exception was never
                    # retrieved" log, not a real problem: the turn lock still
                    # releases correctly either way (handle_user_message's
                    # `async with self._turn_lock` runs its __aexit__ on any
                    # exception), and there's no one left to deliver an error
                    # message to.
                    pass
                return

        if self._stop_requested:
            # Mirrors ChatSession's _format_agent_reply for status ==
            # "stopped" -- same "[stopped]" note, appended rather than
            # replacing whatever text streamed through before the stop.
            reply_text = f"{reply_text}\n\n[stopped]" if reply_text.strip() else "[stopped]"
            await websocket.send_json({"type": "agent_message", "text": reply_text})
        else:
            await websocket.send_json({"type": "agent_message", "text": format_reply(reply_text)})
        # self._last_usage_metadata is set by _stream_turn (see its
        # docstring) -- None if the model never populated usage_metadata at
        # all, in which case the event is omitted entirely rather than
        # showing a fabricated number.
        if self._last_usage_metadata is not None:
            await websocket.send_json(usage_event(self._last_usage_metadata))
        await websocket.send_json({"type": "tasks_changed"})
        if self._wants_title():
            # Off the turn's own path: the reply is done, the title can lag.
            self._title_task = asyncio.create_task(self._name_thread(websocket))
