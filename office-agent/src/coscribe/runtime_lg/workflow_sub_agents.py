"""The sub-agents a workflow's high or full agent step starts (decision 0051).

A sub-agent runs inside the step's tool call, in the foreground, and is held to the step's
rules: its calls go through the same allowlist, read-only rule, hooks and approval mode as the
step's own. What it can't do is wait for a person. Its state lives only as long as the call, so
a call of its that would need an answer is refused, and the step's agent, whose pauses survive a
restart, makes that call itself. A sub-agent starts none of its own.

Its tokens come back with its report, as the tool result's artifact, and count against the
step's budget where it was started (`token_limit.tokens_used`); each one gets what is left of
that budget when it starts."""

from __future__ import annotations

import asyncio
import contextvars
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from ..runtime import redactor, tool_metadata
from ..workflows import SUB_AGENT_TOOL, AgentCall, AgentRequest
from .agent import build_langgraph_agent, tool_name
from .agent_stream import RunRecord, stream_turn
from .messages import extract_text
from .subagent_kinds import subagent_role
from .subagents import LIMIT_MESSAGE_PREFIX, SUBAGENT_MAX_STEPS, wrap_up
from .token_limit import SUB_AGENT_ARTIFACT, TOKEN_LIMIT_PREFIX, since_go_on, sub_agent_usage
from .token_limit import tokens_used as _tokens_used

logger = logging.getLogger(__name__)

_DEFERRAL_TOOLS = frozenset({"search_tools", "use_tool"})

_WORKFLOW_NOTE = (
    "\n\nYou work for one step of a workflow that runs on its own, with no one to ask. A call "
    "that would need a person's approval is refused: leave it, and say in your report what is "
    "still to do so the step can do it. You have at most {max_turns} steps (model calls); stop "
    "as soon as you have enough."
)

NEEDS_A_PERSON = (
    "A sub-agent can't wait for a person's approval, so this call was refused. Leave it, and "
    "say in your report what is still to do."
)


@dataclass(frozen=True)
class Activity:
    """What an agent's messages show it did, with the sub-agents it started."""

    tool_calls: int = 0
    tokens: int = 0
    cached_tokens: int = 0
    tools_used: tuple[str, ...] = ()
    sub_agents: int = 0

    def usage(self) -> dict[str, Any]:
        return {"tokens": self.tokens, "cached_tokens": self.cached_tokens,
                "tool_calls": self.tool_calls, "tools_used": list(self.tools_used)}  # fmt: skip


def activity(messages: Sequence[Any]) -> Activity:
    """Tool calls, tokens, the part of them the provider served from its cache, the tools used,
    and how many sub-agents were started -- whose own calls and tokens are counted in."""
    calls, tokens, cached, children = 0, 0, 0, 0
    used: set[str] = set()
    for message in messages:
        child = sub_agent_usage(message)
        if child is not None:
            children += 1
            calls += int(child.get("tool_calls") or 0)
            tokens += int(child.get("tokens") or 0)
            cached += int(child.get("cached_tokens") or 0)
            used.update(str(name) for name in child.get("tools_used") or [])
        if not isinstance(message, AIMessage):
            continue
        usage: dict[str, Any] = dict(message.usage_metadata or {})
        tokens += int(usage.get("total_tokens", 0) or 0)
        cached += int((usage.get("input_token_details") or {}).get("cache_read", 0) or 0)
        for call in message.tool_calls:
            if call["name"] not in _DEFERRAL_TOOLS:
                calls += 1
                used.add(call["name"])
    return Activity(calls, tokens, cached, tuple(sorted(used)), children)


def sub_agents_started(messages: Sequence[Any]) -> int:
    return sum(1 for message in messages if sub_agent_usage(message) is not None)


@dataclass
class SubAgents:
    """What a step's sub-agents are built from: the step's own tools, model and rules."""

    request: AgentRequest
    # The step's tools, without the sub-agent tool: a sub-agent starts none of its own.
    tools: Sequence[Callable[..., Any] | BaseTool]
    risks: Mapping[str, str]
    model_string: str
    chat_model: Any
    # The step's decision on one of a sub-agent's calls: approve or reject, never wait.
    decide: Callable[[AgentCall], Awaitable[dict[str, Any]]]
    # The message that lets the step's agent go on after its budget, which starts a new one.
    go_on: str
    state_dir: Path
    record_run: Callable[[dict[str, Any]], RunRecord]
    model_stall_seconds: float
    defer_tools: bool
    core_tool_names: frozenset[str]

    def tool(self) -> Callable[..., Any]:
        """The step's `spawn_agent`, as its agent sees it."""
        tools_by_name = {tool_name(t): t for t in self.tools}

        async def spawn_agent(
            description: str,
            prompt: str,
            instructions: str = "",
            tool_names: str = "",
            kind: str = "",
            state: Annotated[dict[str, Any] | None, InjectedState] = None,
            tool_call_id: Annotated[str, InjectedToolCallId] = "",
        ) -> ToolMessage:
            """Hand a self-contained part of this step's task to a sub-agent and wait for its
            report. It sees nothing of this step, so include every path, fact and constraint.
            It runs with this step's model and rules, and a call of its that would need a
            person's approval is refused: make such calls yourself.

            Args:
                description: a few plain words for the run's record.
                prompt: the complete task.
                instructions: its role, if it needs one beyond doing the task.
                tool_names: comma-separated names of your tools to give it; empty gives it
                    all of them.
                kind: a ready-made role, empty for none: "research" finds things and reports
                    each with its source (read-only tools); "check" confirms figures and
                    statements against their sources. instructions and tool_names, when
                    given, take its place.
            """
            del description  # the record names the step; the words stay out of it (0045)

            def answer(text: str, usage: dict[str, Any] | None = None) -> ToolMessage:
                artifact = None if usage is None else {SUB_AGENT_ARTIFACT: usage}
                status = "success" if usage else "error"
                return ToolMessage(
                    text, tool_call_id=tool_call_id, name=SUB_AGENT_TOOL, artifact=artifact,
                    status=status,
                )  # fmt: skip

            requested = [n.strip() for n in tool_names.split(",") if n.strip()]
            unknown = [n for n in requested if n not in tools_by_name]
            if unknown:
                return answer(f"Unknown tool for a sub-agent: {', '.join(unknown)}")
            try:
                role = subagent_role(kind, instructions)
            except ValueError as exc:
                return answer(str(exc))
            cap = self._tokens_left((state or {}).get("messages", []))
            if cap is not None and cap <= 0:
                return answer("This step has used its tokens: finish the task yourself.")
            selected = [tools_by_name[n] for n in requested] or role.tools(tools_by_name.values())
            # A fresh context, as a conversation's sub-agent has: otherwise its graph is taken
            # for a subgraph of the step's, its pauses stop the step, and its words stream out.
            run = asyncio.create_task(
                self._run(role.instructions, prompt, selected, cap, tool_call_id, not requested),
                context=contextvars.Context(),
            )
            text, usage = await run
            return answer(text, usage)

        return tool_metadata(spawn_agent, risk_category="READ", category="subagents")

    def _tokens_left(self, messages: Sequence[Any]) -> int | None:
        if self.request.max_tokens is None:
            return None
        return self.request.max_tokens - _tokens_used(since_go_on(messages, self.go_on))

    async def _run(
        self,
        role: str,
        prompt: str,
        selected: Sequence[Callable[..., Any] | BaseTool],
        cap: int | None,
        call_id: str,
        given_all: bool,
    ) -> tuple[str, dict[str, Any]]:
        """The sub-agent's report and what it used. A failure is its report, not the step's:
        the step's agent decides what to do without it."""
        system = role + _WORKFLOW_NOTE.format(max_turns=SUBAGENT_MAX_STEPS)
        names = [tool_name(t) for t in selected]
        agent = build_langgraph_agent(
            self.chat_model,
            selected,
            system,
            checkpointer=InMemorySaver(),
            extra_interrupt_tool_names=names,
            max_turns=SUBAGENT_MAX_STEPS,
            max_tokens=None if cap is None else (cap, self.go_on),
            # As a conversation's sub-agent: a hand-picked set is small enough to bind as is.
            defer_tools=self.defer_tools
            and given_all
            and any(n not in self.core_tool_names for n in names),
            core_tool_names=self.core_tool_names,
            redact=redactor(self.state_dir),
        )
        config = {"configurable": {"thread_id": f"{self.request.key}-sub-{call_id}"}}
        recorder = self.record_run(
            {"kind": "subagent", "step": self.request.key, "model": self.model_string}
        )
        turn: Any = {"messages": [HumanMessage(prompt)]}
        state: Any = None
        stopped = False
        try:
            while True:
                await stream_turn(agent, turn, config, _ignore, self.model_stall_seconds,
                                  set(), recorder)  # fmt: skip
                state = await agent.aget_state(config)
                if not state.next:
                    break
                resume = await self._decisions(state)
                if not resume:
                    raise RuntimeError("the sub-agent stopped partway with nothing to resume")
                turn = Command(resume=resume)
        except asyncio.CancelledError:
            stopped = True
            raise
        except Exception as exc:
            recorder.failed(exc)
            logger.warning("workflow sub-agent %s failed", config, exc_info=True)
            state = state if state is not None else await agent.aget_state(config)
            error = (str(exc) or type(exc).__name__)[:2000]
            return f"(the sub-agent failed: {error})", activity(_messages(state)).usage()
        finally:
            recorder.finish(stopped=stopped)
        messages = _messages(state)
        text = extract_text(getattr(messages[-1], "content", None)) if messages else ""
        if text.startswith((LIMIT_MESSAGE_PREFIX, TOKEN_LIMIT_PREFIX)):
            try:
                text = await wrap_up(self.chat_model, system, messages)
            except Exception:  # the step's agent hears that it ran out
                logger.warning("workflow sub-agent %s couldn't report", config, exc_info=True)
                text = "(it ran out of steps or tokens before finishing)"
        return text or "(the sub-agent gave no reply)", activity(messages).usage()

    async def _decisions(self, state: Any) -> dict[str, Any]:
        resume: dict[str, Any] = {}
        for task in state.tasks:
            for pending in task.interrupts:
                decisions = []
                for i, action in enumerate(pending.value.get("action_requests", [])):
                    name, args = action["name"], dict(action.get("args") or {})
                    call = AgentCall(f"{pending.id}:{i}", name, args, self.risks.get(name, "EXEC"))
                    decisions.append(await self.decide(call))
                resume[pending.id] = {"decisions": decisions}
        return resume


def _messages(state: Any) -> list[Any]:
    return list((getattr(state, "values", None) or {}).get("messages", []))


async def _ignore(_update: Any) -> None:
    return None
