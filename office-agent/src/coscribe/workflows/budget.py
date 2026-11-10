"""How many tokens a run's models use before a person is asked whether it goes on (decision 0043).
Nobody sets a number: an agent step gets `StepContext.step_tokens` at a time, and a run what its
task's earlier runs used, with room to spare. Going over pauses the run with a question; it never
fails on its own, and never spends on while no one answers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from langgraph.errors import GraphBubbleUp
from langgraph.types import interrupt

from ..workflow_spec import AgentStep, LLMStep, Step
from .step_work import StepContext, StepFailed, StepRecord, now_text

RUN_TOKENS_FLOOR = 2_000_000
RUN_TOKENS_FACTOR = 3


def tokens_of(record: dict[str, Any]) -> int:
    """The new tokens a step's record says its models used (what a provider served from its
    cache is billed far lower): an agent step's, its healing's, or the plan of steps a run
    added. Counted once, when the step ends."""
    if record.get("status") not in ("done", "failed"):
        return 0
    agent = record.get("agent") or {}
    return int(agent.get("tokens") or 0) - int(agent.get("cached_tokens") or 0)


@dataclass
class RunBudget:
    cap: int
    # What a person's "go on" adds: the cap the run's history gave.
    grant: int
    spent: int = 0
    # Keeps a cap a person raised with the run, so the run's next action starts from it.
    keep: Callable[[int], None] | None = None

    def count(self, record: StepRecord) -> None:
        self.spent += tokens_of(record.to_dict())

    def go_on(self, grant: int) -> None:
        # From what was spent when asked, so asking again on resume raises it no further.
        self.cap = max(self.cap, self.spent + grant)
        if self.keep is not None:
            self.keep(self.cap)


def run_budget(
    finished: Iterable[list[dict[str, Any]]],
    steps: list[dict[str, Any]],
    kept: int | None,
    keep: Callable[[int], None] | None = None,
) -> RunBudget:
    """A run's budget from the step records of its task's finished runs, its own records so far
    (a run resumed has spent some), and the cap a person raised it to, if they did."""
    grant = max([RUN_TOKENS_FLOOR, *(RUN_TOKENS_FACTOR * _spent(run) for run in finished)])
    return RunBudget(max(grant, kept or 0), grant, _spent(steps), keep)


def _spent(steps: list[dict[str, Any]]) -> int:
    return sum(tokens_of(record) for record in steps)


class _Builder(Protocol):
    ctx: StepContext
    unattended: bool

    async def emit(self, record: StepRecord) -> None: ...


Scope = Literal["step", "run"]


def _amount(tokens: int) -> str:
    return f"{tokens / 1_000_000:.1f}M" if tokens >= 1_000_000 else f"{round(tokens / 1000)}k"


def _message(step: Step, scope: Scope, used: int) -> str:
    if scope == "step":
        return f"{step.title}: the agent has used {_amount(used)} new tokens and isn't done yet."
    return f"This run has used {_amount(used)} new tokens, more than this task's runs usually use."


async def ask_for_tokens(
    builder: _Builder, step: Step, started: str, it: list[int], scope: Scope, used: int
) -> None:
    """Pause until a person says the run may use more; StepFailed when they say stop, or when
    no one is there to ask. An answer replayed for another pause in the same step is passed
    over by its call id, as an agent's calls are."""
    message = _message(step, scope, used)
    if builder.unattended:
        raise StepFailed(f"{message} No one was there to let it go on.")
    asked = {"kind": "tokens", "until": None, "scope": scope, "used": used}
    call_id = f"tokens-{scope}-{used}"
    while True:
        try:
            answer = interrupt({"step_id": step.id, "title": step.title, "message": message,
                                "call_id": call_id, "pause": asked})  # fmt: skip
        except GraphBubbleUp:
            await builder.emit(StepRecord(step.id, "waiting", started, output=message,
                                          iteration=it, pause=asked))  # fmt: skip
            raise
        answer = answer if isinstance(answer, dict) else {}
        if answer.get("call_id") in (call_id, None):
            break
    if answer.get("approved") is not True:
        raise StepFailed(f"Stopped: {message}", step_id=step.id, declined=True)
    await builder.emit(StepRecord(step.id, "running", started_at=started or now_text(),
                                  iteration=it))  # fmt: skip


async def check_run(builder: _Builder, step: Step, started: str, it: list[int]) -> None:
    """Before a step that uses a model: when the run has spent its cap, ask whether it goes on."""
    budget = builder.ctx.budget
    if budget is None or budget.spent < budget.cap or not isinstance(step, (AgentStep, LLMStep)):
        return
    await ask_for_tokens(builder, step, started, it, "run", budget.spent)
    budget.go_on(budget.grant)
