"""What a step reads: the references in its fields and the texts they are filled into, which
the save-time checks (`scope.py`), permissions and drafting walk."""

from __future__ import annotations

from typing import Any

from .inputs import RELATIVE_DATES
from .refs import is_reference, template_references
from .spec import (
    AgentStep,
    ApprovalStep,
    AskStep,
    BranchStep,
    CheckStep,
    ChoiceStep,
    Condition,
    LLMStep,
    LoopStep,
    ParallelStep,
    RememberStep,
    RunTaskStep,
    ScriptStep,
    Step,
    ToolStep,
    WaitStep,
)


def _condition_refs(condition: Condition) -> list[str]:
    operands = [condition.left] + ([condition.right] if condition.right else [])
    return [r for o in operands if (r := o.reference()) is not None]


def step_references(step: Step) -> list[str]:
    """Every reference a step reads, as written."""
    if isinstance(step, ToolStep):
        return _value_references(step.args)
    if isinstance(step, (ScriptStep, RunTaskStep)):
        return _value_references(step.inputs)
    if isinstance(step, LLMStep):
        return template_references(step.prompt)
    if isinstance(step, AgentStep):
        return template_references(step.goal)
    if isinstance(step, CheckStep):
        return [r for c in step.conditions for r in _condition_refs(c)]
    if isinstance(step, ApprovalStep):
        return template_references(step.message) + [
            r for c in step.when for r in _condition_refs(c)
        ]
    if isinstance(step, AskStep):
        return template_references(step.message) + [f.items for f in step.fields if f.items]
    if isinstance(step, WaitStep):
        return template_references(step.path or "") + _day_reference(step.on)
    if isinstance(step, RememberStep):
        return template_references(step.value)
    if isinstance(step, BranchStep):
        return [r for c in step.conditions for r in _condition_refs(c)]
    if isinstance(step, ChoiceStep):
        return [step.value]
    if isinstance(step, LoopStep):
        # `until` reads the item and the body's results, checked where the body is.
        return [step.over]
    if isinstance(step, ParallelStep):
        return []  # its lanes' steps read, each where it sits
    return []  # pragma: no cover -- every kind is handled above


def _day_reference(on: str | None) -> list[str]:
    """What a wait's day reads: a reference, or the references in a template; a date or a
    relative one reads nothing."""
    if on is None or on in RELATIVE_DATES or not (is_reference(on) or "{{" in on):
        return []
    return [on] if is_reference(on) else template_references(on)


def _value_references(value: Any) -> list[str]:
    if isinstance(value, str):
        return template_references(value)
    if isinstance(value, list):
        return [r for item in value for r in _value_references(item)]
    if isinstance(value, dict):
        return [r for item in value.values() for r in _value_references(item)]
    return []


def _texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [t for item in value for t in _texts(item)]
    if isinstance(value, dict):
        return [t for item in value.values() for t in _texts(item)]
    return []


def step_templates(step: Step) -> list[str]:
    """Every text of a step that references are filled into."""
    if isinstance(step, ToolStep):
        return _texts(step.args)
    if isinstance(step, (ScriptStep, RunTaskStep)):
        return _texts(step.inputs)
    if isinstance(step, LLMStep):
        return [step.prompt]
    if isinstance(step, AgentStep):
        return [step.goal]
    if isinstance(step, (ApprovalStep, AskStep)):
        return [step.message]
    if isinstance(step, RememberStep):
        return [step.value]
    if isinstance(step, WaitStep):
        return [t for t in (step.path, step.on) if t and not is_reference(t)]
    return []
