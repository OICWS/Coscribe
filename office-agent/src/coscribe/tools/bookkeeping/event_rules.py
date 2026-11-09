"""The rule of a task that starts on something from outside: new items in a connector (decision
0039) or an event a program sends it (decision 0040). Both fill a workflow's inputs from what came
in and are held to a number of runs an hour."""

from __future__ import annotations

from typing import Any

from .schedule_rule import DEFAULT_PER_HOUR, MAX_PER_HOUR, ScheduleRule

_WHAT = {"connector": "something new in a connector", "webhook": "an event"}


def event_rule(rule: ScheduleRule, watch: dict[str, Any], workflow: dict[str, Any] | None) -> None:
    """Fill `rule` from `watch`: which input takes which field and the hourly limit, and for a
    connector the tool to ask, its arguments and whether the person vouched for it."""
    if workflow is None:
        raise ValueError(f"Only a task with steps can start on {_WHAT[rule.kind]}")
    inputs_from = watch.get("inputs_from") or {}
    if rule.kind == "connector":
        rule.tool = str(watch.get("tool") or "").strip() or None
        if rule.tool is None:
            raise ValueError(
                "A task that starts on something new in a connector names the tool to ask"
            )
        args = watch.get("args") or {}
        if not isinstance(args, dict) or not isinstance(inputs_from, dict):
            raise ValueError("A connector check's arguments and inputs are each a set of names")
        rule.args = args
        rule.trust_unmarked = bool(watch.get("trust_unmarked", False))
    elif not isinstance(inputs_from, dict):
        raise ValueError("An event's inputs are a set of names")
    names = {i["name"] for i in workflow.get("inputs") or []}
    unknown = sorted(set(inputs_from) - names)
    if unknown:
        raise ValueError(f"The task has no input {unknown[0]!r} to fill from an item")
    rule.inputs_from = {str(k): str(v) for k, v in inputs_from.items()}
    rule.per_hour = int(watch.get("per_hour") or DEFAULT_PER_HOUR)
    if not 1 <= rule.per_hour <= MAX_PER_HOUR:
        raise ValueError(f"A task starts 1 to {MAX_PER_HOUR} runs an hour from new items")
