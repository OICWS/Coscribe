"""Which tasks a workflow task runs as steps (decision 0035), and the checks saving one makes:
each exists and has a workflow, gets every input it needs and has the results the caller reads,
and calls nest at most `MAX_TASK_DEPTH` deep, never in a cycle -- across every stored task, since
saving one task can make a chain through others too deep."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import ValidationError

from ...workflow_spec import (
    MAX_TASK_DEPTH,
    RunTaskStep,
    Workflow,
    parse_workflow,
    step_references,
    task_results,
    walk,
)


class _Store(Protocol):
    def load(self, trigger_id: str) -> Any: ...

    def list_all(self) -> list[Any]: ...


def _parsed(workflow: dict[str, Any] | None) -> Workflow | None:
    try:
        return parse_workflow(workflow) if workflow is not None else None
    except ValidationError:
        return None


def run_task_steps(workflow: Workflow) -> list[RunTaskStep]:
    return [p.step for p in walk(workflow.every_step()) if isinstance(p.step, RunTaskStep)]


def called_ids(workflow: dict[str, Any] | None) -> list[str]:
    parsed = _parsed(workflow)
    steps = run_task_steps(parsed) if parsed is not None else []
    return list(dict.fromkeys(step.task for step in steps))


def called_tasks(store: _Store, workflow: dict[str, Any] | None) -> list[Any]:
    """Every task `workflow` runs, and those they run, each once, nearest first."""
    found: dict[str, Any] = {}
    queue = called_ids(workflow)
    while queue:
        task_id = queue.pop(0)
        if task_id in found:
            continue
        trigger = store.load(task_id)
        if trigger is not None and trigger.workflow is not None:
            found[task_id] = trigger
            queue += called_ids(trigger.workflow)
    return list(found.values())


def check_calls(store: _Store, trigger_id: str, workflow: dict[str, Any] | None) -> None:
    problem = calls_problem(store, trigger_id, workflow)
    if problem:
        raise ValueError(problem)


def calls_problem(store: _Store, trigger_id: str, workflow: dict[str, Any] | None) -> str | None:
    """What is wrong with the tasks `workflow` runs, saved as `trigger_id`; None when nothing."""
    parsed = _parsed(workflow)
    steps = run_task_steps(parsed) if parsed is not None else []
    if parsed is None or not steps:
        return None
    for step in steps:
        problem = _call_problem(store, trigger_id, parsed, step)
        if problem:
            return problem
    stored = [t for t in store.list_all() if t.workflow is not None]
    edges = {t.trigger_id: called_ids(t.workflow) for t in stored}
    edges[trigger_id] = called_ids(workflow)
    names = {t.trigger_id: t.name for t in stored}
    longest = _longest_through(edges, trigger_id)
    chain = " → ".join(f"“{names.get(i, 'this task')}”" for i in longest)
    if len(longest) > 1 and longest[-1] in longest[:-1]:
        return f"Tasks can't run each other in a circle: {chain}"
    if len(longest) - 1 > MAX_TASK_DEPTH:
        return f"Tasks run each other at most {MAX_TASK_DEPTH} deep, not {chain}"
    return None


def _call_problem(
    store: _Store, trigger_id: str, caller: Workflow, step: RunTaskStep
) -> str | None:
    where = f"“{step.title}”"
    if step.task == trigger_id:
        return f"{where} runs the task it is part of; a task can't run itself"
    target = store.load(step.task)
    if target is None:
        return f"{where} runs a task that no longer exists"
    called = _parsed(target.workflow)
    if called is None or not called.steps:
        return f"{where} runs “{target.name}”, which has no steps to run"
    declared = {i.name: i for i in called.inputs}
    unknown = sorted(set(step.inputs) - set(declared))
    if unknown:
        asks = ", ".join(sorted(declared)) or "nothing"
        return f"“{target.name}” has no input {unknown[0]!r}; it asks for {asks}"
    for name, spec in declared.items():
        if spec.required and spec.default in (None, "") and not step.inputs.get(name):
            return f"{where} needs a value for “{spec.label or name}”"
    if step.save_as is None:
        return None
    return _results_problem(caller, step.save_as, target.name, task_results(called))


def _results_problem(
    caller: Workflow, save_as: str, name: str, results: dict[str, list[str] | None]
) -> str | None:
    for placed in walk(caller.every_step()):
        for reference in step_references(placed.step):
            parts = reference.split(".")
            if parts[0] != save_as or len(parts) < 2:
                continue
            where = f"“{placed.step.title}” reads {reference!r}"
            if parts[1] not in results:
                return f"{where}, but “{name}” gives " + (", ".join(results) or "nothing")
            fields = results[parts[1]]
            if len(parts) > 2 and fields is not None and parts[2] not in fields:
                return f"{where}, but {parts[1]} has " + ", ".join(fields)
    return None


def _cycle(edges: dict[str, list[str]], start: str) -> list[str] | None:
    """A chain of calls from `start` that comes back to a task already on it. Every stored task
    was checked when saved, so a new cycle goes through the one being saved."""

    def visit(path: list[str]) -> list[str] | None:
        for following in edges.get(path[-1], []):
            if following in path:
                return [*path[path.index(following) :], following]
            found = visit([*path, following])
            if found:
                return found
        return None

    return visit([start])


def _deepest(ways: dict[str, list[str]], path: list[str]) -> list[str]:
    best = path
    for following in ways.get(path[-1], []):
        if following not in path:
            chain = _deepest(ways, [*path, following])
            best = chain if len(chain) > len(best) else best
    return best


def _longest_through(edges: dict[str, list[str]], start: str) -> list[str]:
    """A cycle through `start`, else the longest chain of calls through it: its callers above,
    then what it runs below."""
    cycle = _cycle(edges, start)
    if cycle is not None:
        return cycle
    callers: dict[str, list[str]] = {}
    for caller, callees in edges.items():
        for callee in callees:
            callers.setdefault(callee, []).append(caller)
    above = _deepest(callers, [start])
    return [*reversed(above[1:]), *_deepest(edges, [start])]


class TaskCalls:
    """The checks above for one store, reached as `ScheduledTriggerStore.calls`."""

    def __init__(self, store: _Store) -> None:
        self.store = store

    def tasks(self, workflow: dict[str, Any] | None) -> list[Any]:
        return called_tasks(self.store, workflow)

    def problem(self, trigger_id: str, workflow: dict[str, Any] | None) -> str | None:
        return calls_problem(self.store, trigger_id, workflow)
