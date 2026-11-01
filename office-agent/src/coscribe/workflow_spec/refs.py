"""Reading values between steps: `{{name}}` / `{{name.field}}` /
`{{name.0}}` in step arguments and prompts, and the operands of a check.
Lookups only -- nothing here evaluates an expression, so a workflow can't
smuggle code in through a reference."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .spec import Condition, Operand

_REFERENCE = r"[a-z][a-z0-9_]*(?:\.[A-Za-z0-9_]+)*"
_TEMPLATE = re.compile(r"\{\{\s*(" + _REFERENCE + r")\s*\}\}")
_ANY_TEMPLATE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
_BARE_REFERENCE = re.compile(r"\s*" + _REFERENCE + r"\s*")
_WHOLE_TEMPLATE = re.compile(r"^\s*\{\{\s*(" + _REFERENCE + r")\s*\}\}\s*$")


class UnresolvedReference(ValueError):
    pass


_PLAIN_REFERENCE = re.compile(_REFERENCE)


def is_reference(text: str) -> bool:
    return _PLAIN_REFERENCE.fullmatch(text) is not None


def template_references(text: str) -> list[str]:
    return _TEMPLATE.findall(text)


def malformed_templates(text: str) -> list[str]:
    """`{{...}}` that isn't a plain reference -- `{{count:x}}`, `{{x | len}}`.
    Rendering leaves these as literal text, so they're refused up front."""
    return [
        match.group(0)
        for match in _ANY_TEMPLATE.finditer(text)
        if not _BARE_REFERENCE.fullmatch(match.group(1))
    ]


def resolve(reference: str, values: dict[str, Any]) -> Any:
    root, *path = reference.split(".")
    if root not in values:
        raise UnresolvedReference(f"{root!r} has no value yet")
    current = values[root]
    walked = root
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
            current = current[int(key)]
        else:
            raise UnresolvedReference(f"{walked!r} has no {key!r}")
        walked = f"{walked}.{key}"
    return current


def as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(
        isinstance(item, (str, int, float)) and not isinstance(item, bool) for item in value
    ):
        return ", ".join(str(item) for item in value)
    return json.dumps(
        value, ensure_ascii=False, indent=2 if isinstance(value, (dict, list)) else None
    )


def render_text(template: str, values: dict[str, Any]) -> str:
    return _TEMPLATE.sub(lambda m: as_text(resolve(m.group(1), values)), template)


def render_value(value: Any, values: dict[str, Any]) -> Any:
    """A step argument with its references filled in. An argument that is
    exactly one reference takes that value as-is (a list stays a list);
    references inside longer text are spliced in as text."""
    if isinstance(value, str):
        whole = _WHOLE_TEMPLATE.fullmatch(value)
        return resolve(whole.group(1), values) if whole else render_text(value, values)
    if isinstance(value, list):
        return [render_value(item, values) for item in value]
    if isinstance(value, dict):
        return {key: render_value(item, values) for key, item in value.items()}
    return value


def operand_value(operand: Operand, values: dict[str, Any]) -> Any:
    if operand.ref is not None:
        return resolve(operand.ref, values)
    if operand.count is not None:
        counted = resolve(operand.count, values)
        if not isinstance(counted, (list, str, dict)):
            raise UnresolvedReference(
                f"can't count {operand.count!r}: it's a {type(counted).__name__}"
            )
        return len(counted)
    return operand.value


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _equal(left: Any, right: Any) -> bool:
    left_number, right_number = _number(left), _number(right)
    if left_number is not None and right_number is not None:
        return left_number == right_number
    return bool(left == right)


def _when(value: Any) -> datetime:
    """A date or a date and time, written the ISO way (2026-03-31, 2026-03-31T09:00)."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    raise UnresolvedReference(f"can't read {value!r} as a date like 2026-03-31")


def _inside(left: Any, right: Any) -> bool:
    if isinstance(left, (list, str, dict)):
        return right in left
    raise UnresolvedReference(f"can't look inside a {type(left).__name__}")


def _empty(value: Any) -> bool:
    return value is None or value in ("", [], {})


def evaluate(condition: Condition, values: dict[str, Any]) -> tuple[bool, Any, Any]:
    """(held, left value, right value) -- the values are what a run record
    shows, so a failed check says what it actually compared."""
    left = operand_value(condition.left, values)
    right = operand_value(condition.right, values) if condition.right is not None else None
    op = condition.op
    if op in ("empty", "not_empty"):
        return _empty(left) == (op == "empty"), left, None
    if op in ("eq", "ne"):
        return _equal(left, right) == (op == "eq"), left, right
    if op in ("contains", "not_contains"):
        return _inside(left, right) == (op == "contains"), left, right
    if op == "starts_with":
        return as_text(left).startswith(as_text(right)), left, right
    if op == "ends_with":
        return as_text(left).endswith(as_text(right)), left, right
    if op in ("before", "after"):
        earlier, later = (
            (_when(left), _when(right)) if op == "before" else (_when(right), _when(left))
        )
        return earlier < later, left, right
    left_number, right_number = _number(left), _number(right)
    if left_number is None or right_number is None:
        raise UnresolvedReference(f"can't compare {left!r} and {right!r} as numbers")
    held = {
        "gt": left_number > right_number,
        "ge": left_number >= right_number,
        "lt": left_number < right_number,
        "le": left_number <= right_number,
    }[op]
    return held, left, right


def conditions_hold(
    conditions: Iterable[Condition], match: str, values: dict[str, Any], settle_early: bool = True
) -> tuple[bool, list[tuple[bool, Any, Any]]]:
    """Whether all the conditions hold, or any one by `match`, and each one checked. It stops at
    the first that settles it, so a later condition may read what an earlier one rules out
    ("no rows, or the first row is late"), unless `settle_early` is off: a check step reports
    every condition that failed."""
    checked = []
    for condition in conditions:
        held, left, right = evaluate(condition, values)
        checked.append((held, left, right))
        if settle_early and held == (match == "any"):
            return held, checked
    each = [c[0] for c in checked]
    return (any(each) if match == "any" and each else all(each)), checked


def same_choice(value: Any, case: str) -> bool:
    """Whether a choice's value picks the path for `case`: as text, ignoring case and spaces."""
    return as_text(value).strip().casefold() == case.strip().casefold()
