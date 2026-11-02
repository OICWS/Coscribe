"""Where a problem sits in a workflow as it was submitted: the step number the editor shows for
a validation error's location, read from the raw JSON because a workflow that fails validation
has no parsed steps to count."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError


def workflow_error(exc: ValidationError, data: Any = None) -> str:
    """One readable line per problem, located by step number (document
    order, as the editor numbers steps -- which takes the submitted `data`
    for a problem inside a branch or loop)."""
    lines = []
    for error in exc.errors():
        number, loc = _locate(data, list(error["loc"]))
        where = f"step {number}: " if number is not None else ""
        field = ".".join(str(part) for part in loc)
        message = str(error["msg"]).removeprefix("Value error, ")
        lines.append(f"{where}{field + ': ' if field else ''}{message}")
    return "; ".join(lines)


_STEP_KINDS = frozenset(
    {"tool", "script", "llm", "agent", "check", "approval", "branch", "choice", "loop"}
)
_RECOVERING_KINDS = frozenset({"tool", "script", "llm", "agent"})


def _raw_arms(step: dict[str, Any]) -> list[tuple[tuple[Any, ...], list[Any]]]:
    """Each step list of a stored step, with where it sits in the step's JSON."""
    if step.get("kind") in _RECOVERING_KINDS:
        failure = step.get("on_failure")
        steps = failure.get("steps") if isinstance(failure, dict) else None
        return [(("on_failure", "steps"), _as_list(steps))]
    if step.get("kind") == "loop":
        return [(("steps",), _as_list(step.get("steps")))]
    cases = _as_list(step.get("cases")) if step.get("kind") == "choice" else []
    paths = [
        (("cases", index, "steps"), _as_list(case.get("steps") if isinstance(case, dict) else None))
        for index, case in enumerate(cases)
    ]
    first = [] if step.get("kind") == "choice" else [(("then",), _as_list(step.get("then")))]
    return [*first, *paths, (("otherwise",), _as_list(step.get("otherwise")))]


def raw_child_lists(step: Any) -> list[list[Any]]:
    """A stored step's own step lists, in document order, read from its JSON: a branch's arms,
    a choice's paths, a loop's body, the steps in a step's place when it fails."""
    return [children for _where, children in _raw_arms(step)] if isinstance(step, dict) else []


def _count(step: Any) -> int:
    return 1 + sum(_count(child) for children in raw_child_lists(step) for child in children)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _locate(data: Any, loc: list[Any]) -> tuple[int | None, list[Any]]:
    if len(loc) < 2 or loc[0] not in ("steps", "after_failure") or not isinstance(loc[1], int):
        return None, loc
    raw = data if isinstance(data, dict) else {}
    steps = _as_list(raw.get(loc[0]))
    # The steps after a failed run are numbered on from the run's own (Workflow.every_step).
    number = sum(_count(s) for s in _as_list(raw.get("steps"))) if loc[0] == "after_failure" else 0
    loc = loc[1:]
    while loc and isinstance(loc[0], int):
        index = loc[0]
        number += sum(_count(s) for s in steps[:index]) + 1
        step = steps[index] if index < len(steps) else None
        loc = loc[1:]
        if loc and loc[0] in _STEP_KINDS:
            loc = loc[1:]
        arms = _raw_arms(step) if isinstance(step, dict) else []
        for position, (where, children) in enumerate(arms):
            inside = loc[len(where) :]
            if tuple(loc[: len(where)]) == where and inside and isinstance(inside[0], int):
                number += sum(_count(s) for _w, earlier in arms[:position] for s in earlier)
                steps, loc = children, inside
                break
        else:
            break
    return number, loc
