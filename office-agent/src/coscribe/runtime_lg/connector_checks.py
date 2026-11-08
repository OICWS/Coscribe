"""Asking a connector for something new, for the tasks that start on it (decision 0039): each due
"connector" task's tool is called with its arguments, and each new item in the answer becomes a
run to start. What was seen and why an item started no run is `tools`' (ConnectorItems); this
module only makes the call, which needs the live connector tools."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..tools import (
    SCHEDULED_THREAD_PREFIX,
    ScheduledTrigger,
    ScheduledTriggerStore,
    connector_of,
    is_read_only,
)
from ..workflows import ask_connector, parse_workflow
from .audit import AuditLog, record_decision

logger = logging.getLogger(__name__)

# A connector that doesn't answer in this long is tried again at the next check.
CHECK_SECONDS = 60

# What a task's run starts with: its task, the run's inputs and what started it.
Started = tuple[str, dict[str, Any], dict[str, Any]]


def forget_paused(store: ScheduledTriggerStore) -> None:
    """A paused task starts from what is there when it resumes, as a timed task doesn't catch up."""
    for trigger in store.list_all():
        if trigger.schedule.kind == "connector" and not trigger.enabled:
            store.connector_items.forget(trigger.trigger_id)


def _refusal(trigger: ScheduledTrigger, tool: Any) -> str | None:
    name = trigger.schedule.tool
    if tool is None:
        return (
            f"{name} isn't available: its connector isn't connected, or the tool is blocked in "
            "Settings > Connectors"
        )
    if not is_read_only(tool) and not trigger.schedule.trust_unmarked:
        return f"{name} isn't marked read-only by its connector; confirm it in the task's settings"
    return None


async def _check(
    store: ScheduledTriggerStore, trigger: ScheduledTrigger, tool: Any, audit: AuditLog
) -> list[Started]:
    rule = trigger.schedule
    refusal = _refusal(trigger, tool)
    if refusal is not None:
        store.connector_items.checked(trigger.trigger_id, error=refusal)
        return []
    answer, error = await ask_connector(tool, rule.args, CHECK_SECONDS)
    starting: list[tuple[str, Any, dict[str, Any]]] = []
    if error is not None:
        store.connector_items.checked(trigger.trigger_id, error=error)
        summary = error
    else:
        specs = list(parse_workflow(trigger.workflow or {}).inputs)
        starting, summary = store.connector_items.take(
            trigger.trigger_id, rule, specs, trigger.runs, answer
        )
    if summary:
        # The call ran with no one asked, so it is on record like a call someone allowed.
        record_decision(audit, thread_id=f"{SCHEDULED_THREAD_PREFIX}{trigger.trigger_id}",
                        tool_name=str(rule.tool), arguments=dict(rule.args), decision="approve",
                        reason="trigger_check", detail=summary)  # fmt: skip
    server = connector_of(tool) or ""
    return [
        (trigger.trigger_id, inputs,
         {"connector": server, "tool": rule.tool, "key": key, "item": item})
        for key, item, inputs in starting
    ]  # fmt: skip


async def check_connectors(
    state_dir: str | Path,
    due: list[ScheduledTrigger],
    connector_tools: Callable[[], list[Any]] | None,
) -> list[Started]:
    """The runs the due tasks' new items start, each due task's tool asked at the same time."""
    if not due:
        return []
    store = ScheduledTriggerStore(state_dir)
    tools = {getattr(t, "name", ""): t for t in (connector_tools() if connector_tools else [])
             if connector_of(t) is not None}  # fmt: skip
    audit = AuditLog(state_dir)
    checks = [_check(store, t, tools.get(t.schedule.tool or ""), audit) for t in due]
    started: list[Started] = []
    for result in await asyncio.gather(*checks, return_exceptions=True):
        if isinstance(result, BaseException):
            logger.error("scheduled_tasks: a connector check failed", exc_info=result)
            continue
        started += result
    return started
