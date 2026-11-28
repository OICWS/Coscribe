"""The runner a workflow's agent step runs through (decision 0028): an agent
built like a sub-agent, kept in the conversation's checkpointer under the
step's key, so a run that pauses on one of its calls -- for an hour, or
across a restart -- goes on from that call instead of starting over.

Every call the agent makes comes to an interrupt, not only the gated ones:
the step's allowlist and its read-only rule are held there, with the same
fixed tool list every agent has (decision 0001), rather than by binding a
smaller one. A call that needs a person ends the pass as "waiting"; the
person's answer comes back on a later pass, named by the call's id, which
is the interrupt's id and the call's place in it, both kept in the
checkpoint."""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command

from ..runtime import get_tool_metadata, redactor
from ..workflows import SUB_AGENT_TOOL, AgentCall, AgentReply, AgentRequest
from .agent import build_langgraph_agent, tool_name
from .agent_stream import MODEL_STALL_SECONDS, ModelStalled, RunRecord, no_record, stream_turn
from .audit import AuditLog, record_decision
from .audit import Reason as AuditReason
from .auto_review import Verdict
from .messages import extract_text
from .subagents import LIMIT_MESSAGE_PREFIX, for_subagents, wrap_up
from .token_limit import TOKEN_LIMIT_PREFIX
from .workflow_sub_agents import NEEDS_A_PERSON, SubAgents, activity, sub_agents_started

logger = logging.getLogger(__name__)

# The code module never runs inside a workflow (decisions 0005, 0028), and
# nobody is there to answer a question.
_NOT_IN_WORKFLOWS = frozenset(
    {"run_code_task", "run_code_command", "ask_user_question", "create_scheduled_task"}
)


def workflow_agent_tools(
    tools: Sequence[Callable[..., Any] | BaseTool],
) -> list[Callable[..., Any] | BaseTool]:
    """The tools an agent step may be given: a sub-agent's, without the
    code module or anything that needs a person."""
    return [t for t in tools if for_subagents(t) and tool_name(t) not in _NOT_IN_WORKFLOWS]


class _Answers:
    """A person's answers to the calls of one pending interrupt that has
    more than one: each comes on its own pass, and all are needed before
    the agent can resume. Kept on disk because a pass can be a day apart."""

    def __init__(self, state_dir: Path, key: str) -> None:
        self.path = state_dir / "workflow_agents" / f"{key}.json"

    def load(self) -> dict[str, dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, answers: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(answers), encoding="utf-8")

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


@dataclass(frozen=True)
class _Decided:
    decision: dict[str, Any]
    # Why, for the audit log; None for a call nothing gates.
    reason: AuditReason | None

    @staticmethod
    def reject(reason: AuditReason, message: str) -> _Decided:
        return _Decided({"type": "reject", "message": message}, reason)


@dataclass
class WorkflowAgentRunner:
    """`workflows.AgentRunner` for a conversation's workflow runs: what
    that conversation gives its agent steps."""

    # The workflow run's thread, for the audit log.
    thread_id: str
    state_dir: Path
    checkpointer: Any
    tools: Sequence[Callable[..., Any] | BaseTool]
    # A step's model, or None for the task's; returns (model string, chat model).
    resolve_model: Callable[[str | None], tuple[str, Any]]
    defer_tools: bool = False
    core_tool_names: frozenset[str] = frozenset()
    fixed_tool_names: frozenset[str] = frozenset()
    keeps_tool_list_fixed: Callable[[str], bool] = lambda _model: False
    # The person's PreToolUse hooks: a reason to refuse the call, or None.
    pre_tool_use: Callable[[str, dict[str, Any]], Awaitable[str | None]] | None = None
    model_stall_seconds: float = MODEL_STALL_SECONDS
    # A record of how each pass of a step went, from what the pass is (its step and model).
    record_run: Callable[[dict[str, Any]], RunRecord] = no_record
    # Auto mode's reviewer on a call, weighed against what the step was saved to do
    # (`AgentRequest.review_as`); None when it gave no verdict.
    review: Callable[[AgentCall, str], Awaitable[Verdict | None]] | None = None

    def __post_init__(self) -> None:
        self._tools = workflow_agent_tools(self.tools)
        self._risks = {
            tool_name(t): get_tool_metadata(cast(Any, t)).risk_category for t in self._tools
        }
        # A step's sub-agents (decision 0051): the tool is on every step's list, so the list
        # stays the same (decision 0001); a step that may start none is refused the call.
        self._risks[SUB_AGENT_TOOL] = "READ"
        # A pass decides every pending call again after one waited: asked once per call.
        self._verdicts: dict[str, Verdict | None] = {}

    async def __call__(self, request: AgentRequest) -> AgentReply:
        # A fresh context: run inside a workflow node, the agent's graph
        # would otherwise be taken for a subgraph of the workflow's, and its
        # interrupts would stop the workflow with the agent's payload.
        return await asyncio.create_task(self._run(request), context=contextvars.Context())

    async def _run(self, request: AgentRequest) -> AgentReply:
        model_string, chat_model = self.resolve_model(request.model)
        agent = self._build(request, model_string, chat_model)
        config = {"configurable": {"thread_id": request.key}}
        answers = _Answers(self.state_dir, request.key)
        # One line per pass: a step that stops to wait for a person leaves a line, and the
        # pass that resumes it another.
        recorder = self.record_run(
            {"kind": "workflow_agent", "step": request.key, "model": model_string}
        )
        stopped = False
        try:
            return await self._passes(request, agent, config, answers, chat_model, recorder)
        except asyncio.CancelledError:
            stopped = True
            raise
        except Exception as error:
            recorder.failed(error)
            raise
        finally:
            recorder.finish(stopped=stopped)

    async def _passes(
        self,
        request: AgentRequest,
        agent: Any,
        config: dict[str, Any],
        answers: _Answers,
        chat_model: Any,
        recorder: RunRecord,
    ) -> AgentReply:
        state = await agent.aget_state(config)
        turn: Any = None
        if not state.values:
            turn = {"messages": [HumanMessage(request.task)]}
        running: set[str] = set()
        try:
            while True:
                if turn is not None:
                    await stream_turn(
                        agent, turn, config, _ignore, self.model_stall_seconds, running, recorder
                    )
                state = await agent.aget_state(config)
                if not state.next:
                    if _out_of_tokens(state):
                        if not request.go_on:
                            return self._reply("over_budget", state)
                        turn = {"messages": [HumanMessage(_GO_ON)]}
                        request = replace(request, go_on=False)
                        continue
                    if _ended_silently(state) and not _was_nudged(state):
                        turn = {"messages": [HumanMessage(_SILENT_END_NUDGE)]}
                        continue
                    break
                resume, waiting = await self._decide(state, request, answers)
                if waiting is not None:
                    return self._reply("waiting", state, call=waiting)
                if not resume:
                    raise RuntimeError("the agent stopped partway with nothing to resume")
                answers.clear()
                turn = Command(resume=resume)
        except ModelStalled as exc:
            recorder.failed(exc)
            return self._reply("failed", state, error=str(exc))
        except Exception as exc:  # noqa: BLE001 -- the step fails with the agent's error
            recorder.failed(exc)
            logger.warning("workflow agent %s failed", request.key, exc_info=True)
            return self._reply("failed", state, error=(str(exc) or type(exc).__name__)[:2000])
        answers.clear()
        if _ended_silently(state):
            return self._reply("failed", state, error=_SILENT_END_ERROR)
        messages = list((state.values or {}).get("messages", []))
        text = extract_text(getattr(messages[-1], "content", None)) if messages else ""
        if text.startswith(LIMIT_MESSAGE_PREFIX):
            try:
                text = await wrap_up(chat_model, request.instructions, messages)
            except Exception:  # noqa: BLE001 -- the step's check sees what is missing
                logger.warning("workflow agent %s couldn't report", request.key, exc_info=True)
                text = f"(it used all {request.max_steps} of its steps before finishing)"
        return self._reply("done", state, text=text)

    def _build(self, request: AgentRequest, model_string: str, chat_model: Any) -> Any:
        core_names = self.core_tool_names
        if self.keeps_tool_list_fixed(model_string):
            core_names = core_names | self.fixed_tool_names
        return build_langgraph_agent(
            chat_model,
            [*self._tools, self._sub_agents(request, model_string, chat_model).tool()],
            request.instructions,
            checkpointer=self.checkpointer,
            extra_interrupt_tool_names=list(self._risks),
            max_turns=request.max_steps,
            max_tokens=None if request.max_tokens is None else (request.max_tokens, _GO_ON),
            defer_tools=self.defer_tools,
            core_tool_names=core_names,
            redact=redactor(self.state_dir),
        )

    def _sub_agents(self, request: AgentRequest, model_string: str, chat_model: Any) -> SubAgents:
        async def decide(call: AgentCall) -> dict[str, Any]:
            outcome = await self._decision(call, request, None)
            if outcome is None:
                outcome = _Decided.reject("workflow_step", NEEDS_A_PERSON)
            if outcome.reason is not None:
                self._audit(call, outcome)
            return outcome.decision

        core_names = self.core_tool_names
        if self.keeps_tool_list_fixed(model_string):
            core_names = core_names | self.fixed_tool_names
        return SubAgents(
            request=request,
            tools=self._tools,
            risks=self._risks,
            model_string=model_string,
            chat_model=chat_model,
            decide=decide,
            go_on=_GO_ON,
            state_dir=self.state_dir,
            record_run=self.record_run,
            model_stall_seconds=self.model_stall_seconds,
            defer_tools=self.defer_tools,
            core_tool_names=core_names,
        )

    async def _decide(
        self, state: Any, request: AgentRequest, answers: _Answers
    ) -> tuple[dict[str, Any], AgentCall | None]:
        """The decisions for every pending call, or the first call still
        waiting for a person. Decisions are recorded only once they are
        sent, so a pass that stops to wait records nothing twice."""
        given = answers.load()
        answer = request.answer
        resume: dict[str, Any] = {}
        decided: list[tuple[AgentCall, _Decided]] = []
        waiting: AgentCall | None = None
        # Counted from the checkpoint, so a resumed pass doesn't hand out the cap again.
        sub_agents_left = request.sub_agents - sub_agents_started(_messages(state))
        for task in state.tasks:
            for pending in task.interrupts:
                decisions = []
                for i, action in enumerate(pending.value.get("action_requests", [])):
                    name, args = action["name"], dict(action.get("args") or {})
                    call = AgentCall(f"{pending.id}:{i}", name, args, self._risks.get(name, "EXEC"))
                    if answer is not None and answer.get("call_id") == call.call_id:
                        given[call.call_id] = answer
                        answers.save(given)
                    starts = call.tool == SUB_AGENT_TOOL
                    outcome = (
                        _Decided.reject("workflow_step", _no_more_sub_agents(request))
                        if starts and sub_agents_left <= 0
                        else await self._decision(call, request, given.get(call.call_id))
                    )
                    if starts and outcome is not None and outcome.decision["type"] == "approve":
                        sub_agents_left -= 1
                    if outcome is None:
                        waiting = waiting or call
                        continue
                    decided.append((call, outcome))
                    decisions.append(outcome.decision)
                resume[pending.id] = {"decisions": decisions}
        if waiting is not None:
            return {}, waiting
        for call, outcome in decided:
            if outcome.reason is not None:
                self._audit(call, outcome)
        return resume, None

    async def _decision(
        self, call: AgentCall, request: AgentRequest, answer: dict[str, Any] | None
    ) -> _Decided | None:
        if not request.allows(call):
            return _Decided.reject("workflow_step", "This step isn't allowed to make that call.")
        if self.pre_tool_use is not None:
            reason = await self.pre_tool_use(call.tool, call.args)
            if reason is not None:
                return _Decided.reject("hook_veto", reason)
        if answer is not None:
            if answer.get("approved") is True:
                return _Decided({"type": "approve"}, "human")
            return _Decided.reject("human", str(answer.get("note") or "") or "Declined.")
        decision = request.decide(call)
        if decision == "approve":
            # A read the step allows is ungated, as in a conversation: nothing to record.
            return _Decided({"type": "approve"}, None if call.risk == "READ" else "workflow_step")
        if decision == "reject":
            return _Decided.reject("workflow_step", "Not allowed in this run.")
        return await self._reviewed(call, request)

    async def _reviewed(self, call: AgentCall, request: AgentRequest) -> _Decided | None:
        """The reviewer's verdict on a call the step would put to a person, or None to wait."""
        if request.review_as is None or self.review is None:
            return None
        if call.call_id not in self._verdicts:
            self._verdicts[call.call_id] = await self.review(call, request.review_as)
        verdict = self._verdicts[call.call_id]
        if verdict is None:
            return None
        if verdict.allow:
            return _Decided({"type": "approve"}, "auto_review")
        message = f"The reviewer blocked this: {verdict.reason} Find another way."
        return _Decided.reject("auto_review_block", message)

    def _audit(self, call: AgentCall, outcome: _Decided) -> None:
        assert outcome.reason is not None
        record_decision(
            AuditLog(self.state_dir),
            thread_id=self.thread_id,
            tool_name=call.tool,
            arguments=call.args,
            decision="approve" if outcome.decision["type"] == "approve" else "reject",
            reason=outcome.reason,
            detail=outcome.decision.get("message"),
        )

    def _reply(
        self,
        status: Any,
        state: Any,
        *,
        text: str = "",
        call: AgentCall | None = None,
        error: str | None = None,
    ) -> AgentReply:
        done = activity(_messages(state))
        return AgentReply(
            status, text=text, call=call, error=error, tool_calls=done.tool_calls,
            tokens=done.tokens, cached_tokens=done.cached_tokens, tools_used=list(done.tools_used),
            sub_agents=done.sub_agents,
        )  # fmt: skip


async def _ignore(_update: Any) -> None:
    return None


def _no_more_sub_agents(request: AgentRequest) -> str:
    if request.sub_agents <= 0:
        return "This step can't start sub-agents: do the task with your own tools."
    return f"This step has started its {request.sub_agents} sub-agents: do the rest yourself."


# A model can end a turn with no words and no call -- seen after a tool
# error -- and an empty report would pass for a finished step though the
# work may not be done. It is asked once to say where things stand.
_SILENT_END_NUDGE = (
    "Your last reply was empty. If a call failed, deal with it and finish the task. "
    "Then say what you did, and plainly what is not done and why."
)
_SILENT_END_ERROR = "The agent stopped without saying whether the task was done."


def _ended_silently(state: Any) -> bool:
    messages = list((getattr(state, "values", None) or {}).get("messages", []))
    if not messages or not isinstance(messages[-1], AIMessage):
        return False
    last = messages[-1]
    return not last.tool_calls and not extract_text(last.content).strip()


def _was_nudged(state: Any) -> bool:
    messages = (getattr(state, "values", None) or {}).get("messages", [])
    return any(isinstance(m, HumanMessage) and m.content == _SILENT_END_NUDGE for m in messages)


# A person let an agent that used its tokens go on (decision 0043): it carries on where it
# stopped, with as many again.
_GO_ON = "You may use more tokens now. Carry on with the task from where you stopped."


def _messages(state: Any) -> list[Any]:
    return list((getattr(state, "values", None) or {}).get("messages", []))


def _out_of_tokens(state: Any) -> bool:
    messages = _messages(state)
    last = messages[-1] if messages else None
    return isinstance(last, AIMessage) and extract_text(last.content).startswith(TOKEN_LIMIT_PREFIX)
