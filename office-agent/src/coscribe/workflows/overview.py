"""The one sentence the simple view opens a task with: what it does, for someone who will never
read its steps. A model writes it from the steps' own titles, once per saved version."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import TAG_NOSTREAM

from ..workflow_spec import Step, Workflow, child_lists

OVERVIEW_CHARS = 200
# Enough for a long task's titles; past it the sentence would say no more.
_OUTLINE_CHARS = 6000

OVERVIEW_INSTRUCTIONS = """\
You write the one sentence a person reads first on a task's page: what the task does for them.
They will never read its steps. Write one plain English sentence of at most 25 words, starting
with a verb ("Gathers ...", "Checks ..."). Say what it works on and what they get at the end.
Leave out tool names, field names, step counts and how it is built. Reply with the sentence only."""


def _detail(step: Step) -> str:
    fields = getattr(step, "fields", None) or []
    if step.kind in ("llm", "agent") and fields:
        named = "; ".join(f"{f.name}: {f.description}" if f.description else f.name for f in fields)
        return f" (works out {named})"
    if step.kind == "tool":
        return f" ({step.tool})"
    return ""


def _arm(step: Step, arm: str) -> str:
    """An arm as the step names it: a lane by its label, a case by its value."""
    kind, _, index = arm.partition(":")
    if kind == "lane":
        return f"at the same time, {step.lanes[int(index)].label}"  # type: ignore[union-attr]
    if kind == "case":
        return f"when {step.cases[int(index)].is_}"  # type: ignore[union-attr]
    return {"steps": "each item", "fallback": "if it fails"}.get(arm, arm)


def _outline(steps: list[Step], depth: int = 0) -> list[str]:
    lines: list[str] = []
    for step in steps:
        lines.append(f"{'  ' * depth}- {step.kind}: {step.title}{_detail(step)}")
        for arm, children in child_lists(step):
            if children:
                lines.append(f"{'  ' * (depth + 1)}{_arm(step, arm)}:")
                lines.extend(_outline(children, depth + 2))
    return lines


def overview_request(name: str, workflow: Workflow) -> str:
    """What the model is shown: the task's name, what it asks for and its steps by title."""
    asks = ", ".join(i.label or i.name for i in workflow.inputs) or "nothing"
    outline = "\n".join(_outline(workflow.steps))[:_OUTLINE_CHARS]
    return f"Task: {name}\nAsks for: {asks}\nSteps:\n{outline}"


def clean_overview(text: str) -> str:
    """One line, without the quotes or label a model may wrap it in, at most OVERVIEW_CHARS."""
    line = " ".join(text.split()).strip().strip("\"'“”").strip()
    if line.lower().startswith("overview:"):
        line = line[len("overview:") :].strip()
    if len(line) > OVERVIEW_CHARS:
        line = line[: OVERVIEW_CHARS - 1].rsplit(" ", 1)[0] + "…"
    return line


async def write_overview(model: Any, name: str, workflow: Workflow) -> str:
    """The sentence, or "" when the model gave nothing usable."""
    reply = await model.ainvoke(
        [
            SystemMessage(content=OVERVIEW_INSTRUCTIONS),
            HumanMessage(content=overview_request(name, workflow)),
        ],
        config={"tags": [TAG_NOSTREAM]},
    )
    content = reply.content
    if isinstance(content, list):
        # A thinking model answers in blocks; only its text blocks are the sentence.
        content = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return clean_overview(str(content))
