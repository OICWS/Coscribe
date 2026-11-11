"""Putting a conversation's agent together: which tools it is bound with, which of them
are approval-gated, how many are deferred behind search_tools, and what the context panel
measures. The session keeps the live state; this reads it and builds from it."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from functools import cached_property
from pathlib import Path
from typing import Any, Protocol, cast

from langchain_core.messages.ai import UsageMetadata
from langchain_core.tools import BaseTool

from ..code_runtime import code_service
from ..config import Settings, side_model_name
from ..coordinator import CORE_TOOL_NAMES
from ..runtime import LLMClient, SessionEnvironments, get_tool_metadata, redactor
from ..runtime_lg import (
    CODE_APPROVAL_RISKS,
    CODE_TASK_TOOL,
    CodeTaskContext,
    SubAgentHost,
    bound_tool_names,
    build_code_task_tool,
    build_delegation_tools,
    build_langgraph_agent,
    build_review_work_tool,
    build_search_tools_tool,
    build_use_tool_tool,
    keeps_tool_list_fixed,
    resolve_chat_model,
    select_reviewer_tools,
    tool_name,
)
from ..tools import (
    QUESTION_TOOL_NAMES,
    TASK_DRAFT_TOOL_NAMES,
    TaskToolkit,
    WorkspaceScope,
    format_skill_listing,
    load_builtin_skills,
    load_skills,
)
from ..tools.web import build_http_tools
from .artifact_tools import build_artifact_tools
from .connector_offer import ConnectorDirectory as ConnectorDirectory
from .connector_offer import build_connector_offer_tools
from .context_usage import build_context_breakdown
from .folder_brief import FolderBriefKeeper
from .page_tools import build_page_tools
from .save_offer import SaveOffer
from .turn_text import build_instructions
from .workspace_folder import WorkspaceFolders


class AssemblyHost(Protocol):
    """What the assembly reads on the session it builds for."""

    thread_id: str
    settings: Settings
    workspace_root: Path
    extra_folders: list[Path]
    enabled_skill_names: set[str]
    hooks_config: dict[str, list[str]]
    model: Any
    _model_string: str
    _instructions: str
    _checkpointer: Any
    _custom_providers: dict[str, dict[str, str]]
    _context_window_client: LLMClient
    _context_window: int | None
    _last_usage_metadata: UsageMetadata | None
    _base_tools: list[Callable[..., Any] | BaseTool]
    _extra_tools: list[Callable[..., Any] | BaseTool]
    # Read by SaveOffer at the end of a turn.
    lg_agent: Any
    config: Any
    _stop_requested: bool
    _pending_approvals: dict[str, Any]
    _pending_questions: dict[str, Any]
    connector_directory: ConnectorDirectory | None

    def is_workflow_run(self) -> bool: ...

    def workspace_scope(self) -> WorkspaceScope: ...

    def tool_catalog(self) -> dict[str, Any]: ...

    def _subagent_host(self, model: Any) -> SubAgentHost: ...

    def _build_draft_workflow_tool(self) -> BaseTool: ...

    def _build_revise_workflow_tool(self) -> BaseTool: ...

    def _build_test_workflow_tool(self) -> BaseTool: ...

    async def _take_steers(self) -> list[tuple[str, list[str]]]: ...


def risks_of_gated_tools(lg_tools: list[Any]) -> dict[str, str]:
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


class AgentAssembly:
    def __init__(self, host: AssemblyHost) -> None:
        self._host = host
        self._side: tuple[str, Any] | None = None

    @cached_property
    def folder_briefs(self) -> FolderBriefKeeper:
        return FolderBriefKeeper(
            Path(self._host.settings.state_dir),
            self.side_model,
            lambda: self._host.settings.folder_briefs,
        )

    @cached_property
    def workspace_folders(self) -> WorkspaceFolders:
        return WorkspaceFolders(Path(self._host.settings.state_dir))

    @cached_property
    def save_offer(self) -> SaveOffer:
        return SaveOffer(self._host, self.side_model)

    def folders(self) -> list[Path]:
        return [Path(self._host.workspace_root), *self._host.extra_folders]

    def shown_folders(self) -> list[dict[str, Any]]:
        """For the side panel: each folder's brief and what it keeps in `.coscribe/`."""
        return [
            {**brief, "workspace": self.workspace_folders.shown(Path(brief["path"]))}
            for brief in self.folder_briefs.shown(self.folders())
        ]

    def context(self, described: str) -> str:
        """`described` with what the folders hold and the notes and skills they keep."""
        folders = self.folders()
        return self.workspace_folders.context(
            self.folder_briefs.context(described, folders), folders
        )

    def side_model(self) -> Any:
        """The model for side jobs around a turn (`Settings.side_model`): the reviewer, the title,
        the suggestion. A picked model falls back to the conversation's, so a key without access
        to it still gets a title and a verdict."""
        main = self._host.model
        name = side_model_name(self._host._model_string, self._host.settings.side_model)
        if name == self._host._model_string:
            return main
        if self._side is None or self._side[0] != name:
            try:
                small = resolve_chat_model(name, self._host._custom_providers)
            except (ValueError, ImportError):
                # A picked model that can't be built (a provider since removed) only costs more.
                return main
            self._side = (name, small)
        return self._side[1].with_fallbacks([main])

    def build_lg_tools(self, model: Any) -> list[Callable[..., Any] | BaseTool]:
        # self._host._base_tools ("domain" tools) combined with self._host._extra_tools
        # (MCP connector tools -- see __init__'s comment on why these are
        # kept separate) *before* appending spawn_agent itself below -- a
        # sub-agent's own
        # selectable tool_names never includes spawn_agent, and does include
        # MCP tools.
        combined_tools = [*self._host._base_tools, *self._host._extra_tools]
        delegation_tools = build_delegation_tools(self._host._subagent_host(model), combined_tools)
        # The reviewer only ever gets read-only tools (document readers and
        # file listing/reading) -- independent verification of a generated
        # file's real content, never a way for it to change anything. See
        # select_reviewer_tools for why that also keeps it from pausing on
        # an approval.
        reviewer_tools = select_reviewer_tools(combined_tools)
        review_work_tool = build_review_work_tool(
            model, reviewer_tools, self._host.settings.state_dir
        )
        code_tools: list[Callable[..., Any]] = []
        if self._host.settings.code_module_enabled:
            code_tools.append(
                build_code_task_tool(
                    self._host._subagent_host(model),
                    CodeTaskContext(
                        service=lambda: code_service(self._host.settings),
                        model=lambda: self._host.settings.code_model or self._host._model_string,
                        folder=lambda: Path(self._host.workspace_root),
                        context_window=lambda: self._host._context_window_client.get_context_window(
                            self._host.settings.code_model or self._host._model_string
                        ),
                        env=lambda: SessionEnvironments(self._host.settings.state_dir).get(
                            self._host.thread_id
                        )["variables"],
                    ),
                )
            )
        directory = self._host.connector_directory
        offer_tools = (
            build_connector_offer_tools(
                directory,
                self._host.settings.state_dir,
                self._host.thread_id,
                self._host.is_workflow_run,
            )
            if directory is not None
            else []
        )
        return [
            *combined_tools,
            *delegation_tools,
            *code_tools,
            *offer_tools,
            *build_http_tools(self._host.settings.state_dir, self._host.thread_id),
            *build_artifact_tools(self._host.settings.state_dir, self._host.workspace_scope),
            *build_page_tools(
                self._host.workspace_scope, self._host.settings.state_dir, self._host.thread_id
            ),
            review_work_tool,
            self._host._build_draft_workflow_tool(),
            self._host._build_revise_workflow_tool(),
            self._host._build_test_workflow_tool(),
        ]

    def build_lg_agent(
        self, model: Any, model_string: str, lg_tools: list[Callable[..., Any] | BaseTool]
    ) -> Any:
        # When PreToolUse hooks are configured, route *every* tool call
        # through the same interrupt point -- not just the ones that
        # already require human approval -- so a hook gets the chance to
        # veto a low-risk tool too, not just a gated one.
        extra_interrupt_names = (
            [tool_name(t) for t in lg_tools] if self._host.hooks_config["PreToolUse"] else []
        )
        # `model_string` is taken as its own parameter rather than read from
        # self._host._model_string -- switch_model (below) calls this *before*
        # updating self._host._model_string (so a failed switch can revert
        # cleanly without ever having mutated it), so reading the field
        # here would silently compute auto_compact_tokens for the *old*
        # model on every switch. get_context_window is best-effort and
        # never raises (see LLMClient.get_context_window's own docstring),
        # so no try/except is needed around it here.
        auto_compact_tokens = max(
            1,
            int(
                self._host._context_window_client.get_context_window(model_string)
                * self._host.settings.auto_compact_threshold
            ),
        )
        core_names, defer = self.tool_binding(model_string, lg_tools)
        return build_langgraph_agent(
            model,
            lg_tools,
            build_instructions(self._host._instructions, defer_tools=defer),
            checkpointer=self._host._checkpointer,
            extra_interrupt_tool_names=extra_interrupt_names,
            question_tool_names=QUESTION_TOOL_NAMES | TASK_DRAFT_TOOL_NAMES,
            max_turns=self._host.settings.max_turns,
            auto_compact_tokens=auto_compact_tokens,
            defer_tools=defer,
            core_tool_names=core_names,
            take_steers=self._host._take_steers,
            redact=redactor(self._host.settings.state_dir),
            resolve_file=lambda path: self._host.workspace_scope().resolve(path),
            open_tasks=lambda: TaskToolkit(
                self._host.thread_id, self._host.settings.state_dir
            ).open_tasks_note(),
        )

    def tool_binding(
        self, model_string: str, tools: Sequence[Callable[..., Any] | BaseTool]
    ) -> tuple[frozenset[str], bool]:
        """(the tools bound from the first request, whether any are left
        for search_tools). Connector tools stay deferred everywhere: four
        connectors were 394k tokens of schemas."""
        core = CORE_TOOL_NAMES
        if keeps_tool_list_fixed(model_string, self._host._custom_providers):
            connector_names = {tool_name(t) for t in self._host._extra_tools}
            core = core | {tool_name(t) for t in tools if tool_name(t) not in connector_names}
        defer = self._host.settings.defer_tools and any(tool_name(t) not in core for t in tools)
        return core, defer

    async def context_breakdown(self) -> dict[str, Any]:
        """Where this thread's context-window budget actually goes --
        backs the context-usage panel (ContextRing.tsx's expanded view).
        See context_usage.py's own module docstring for the measurement
        approach and its documented approximation.

        Recomputes the currently-enabled skills' own listing text fresh
        (rather than trying to re-extract it from the already-concatenated
        self._host._instructions) via the exact same load-then-filter-by-name
        expression __init__/set_enabled_skills/switch_model already use
        to build self._host._instructions in the first place -- guaranteed to
        match, since self._host.enabled_skill_names is the one shared input
        every one of those call sites feeds into build_coordinator_agent's
        own identical filter."""
        if self._host._context_window is None:
            self._host._context_window = await asyncio.to_thread(
                self._host._context_window_client.get_context_window, self._host._model_string
            )
        skills = [
            skill
            for skill in load_builtin_skills() + load_skills(self._host.settings.skills_dir)
            if skill.name in self._host.enabled_skill_names
        ]
        skills_listing = format_skill_listing(skills) if skills else ""
        last_total = (
            self._host._last_usage_metadata["total_tokens"]
            if self._host._last_usage_metadata
            else None
        )
        base_tools = list(self._host._base_tools)
        mcp_tools = list(self._host._extra_tools)
        core_names, defer = self.tool_binding(self._host._model_string, [*base_tools, *mcp_tools])
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
            instructions=build_instructions(self._host._instructions, defer_tools=defer),
            skills_listing=skills_listing,
            base_tools=base_tools,
            mcp_tools=mcp_tools,
            context_window=self._host._context_window or 0,
            auto_compact_threshold=self._host.settings.auto_compact_threshold,
            last_total_tokens=last_total,
        )


class _RebuildsOnUse(Protocol):
    def apply_pending_tools(self) -> None: ...


class RebuiltOnUse:
    """An attribute of a conversation that a connector change makes stale (its agent, its connector
    tools, the risks of its gated tools), read through `apply_pending_tools`: rebuilt on first use,
    not when the change is made, since rebuilding every open conversation at once ran on the
    server's loop, about a second each, and with dozens open held the whole server."""

    def __set_name__(self, owner: type, name: str) -> None:
        self._slot = f"_{name}_built"

    def __get__(self, host: _RebuildsOnUse | None, owner: type | None = None) -> Any:
        if host is None:
            return self
        host.apply_pending_tools()
        return vars(host)[self._slot]

    def __set__(self, host: _RebuildsOnUse, value: Any) -> None:
        vars(host)[self._slot] = value
