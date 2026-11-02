"""The kinds of value a workflow asks for at each run (decision 0031), and the dates a date input
can default to, worked out on the day each run starts. The frontend mirrors these in
`frontend/src/lib/inputKinds.ts`."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any, Literal, Protocol

InputType = Literal["text", "number", "date", "choice", "yes_no", "file", "folder"]

RELATIVE_DATES = (
    "today",
    "yesterday",
    "week_start",
    "last_week_start",
    "last_week_end",
    "month_start",
    "last_month_start",
    "last_month_end",
    "year_start",
)

_YES = frozenset({"yes", "true", "y", "1"})
_NO = frozenset({"no", "false", "n", "0"})


def resolve_date(name: str, today: date) -> str:
    """The ISO date a relative default stands for on `today`."""
    monday = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    days = {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "week_start": monday,
        "last_week_start": monday - timedelta(days=7),
        "last_week_end": monday - timedelta(days=1),
        "month_start": month_start,
        "last_month_start": last_month_end.replace(day=1),
        "last_month_end": last_month_end,
        "year_start": today.replace(month=1, day=1),
    }
    return days[name].isoformat()


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return len(value) == 10


def _yes_no(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().casefold()
    return True if text in _YES else False if text in _NO else None


def _number(name: str, given: Any) -> int | float:
    if isinstance(given, bool):
        raise ValueError(f"input {name!r} needs a number, not {given!r}")
    try:
        number = float(str(given).strip())
    except ValueError:
        raise ValueError(f"input {name!r} needs a number, not {given!r}") from None
    return int(number) if number.is_integer() else number


def input_problem(kind: InputType, default: Any, options: list[str]) -> str | None:
    """Why an input's definition doesn't hold together, or None."""
    if kind == "choice":
        cleaned = [o.strip() for o in options]
        if not cleaned or any(not o for o in cleaned):
            return "a choice lists its options, none of them blank"
        if len({o.casefold() for o in cleaned}) != len(cleaned):
            return "each option of a choice is listed once"
    elif options:
        return "only a choice has options"
    if default is None or default == "":
        return None
    if kind == "date" and not (default in RELATIVE_DATES or _is_iso_date(str(default))):
        return f"{default!r} isn't a date (YYYY-MM-DD) or one of {', '.join(RELATIVE_DATES)}"
    if kind == "yes_no" and not isinstance(default, bool):
        return "a yes-or-no input defaults to true or false"
    if kind == "choice" and str(default).strip().casefold() not in {
        o.strip().casefold() for o in options
    }:
        return f"{default!r} isn't one of its options"
    return None


class _Input(Protocol):
    # Read-only, so an ask step's field, which can also be a pick, is one too.
    @property
    def name(self) -> str: ...
    @property
    def type(self) -> str: ...
    @property
    def default(self) -> Any: ...
    @property
    def options(self) -> list[str]: ...
    @property
    def required(self) -> bool: ...


def default_value(spec: _Input, today: date) -> Any:
    """An input's default as a run would get it: a relative date as the day it stands for."""
    if spec.type == "date" and spec.default in RELATIVE_DATES:
        return resolve_date(str(spec.default), today)
    return spec.default


def input_value(spec: _Input, given: Any) -> Any:
    """The value a run's steps get for `spec`, from what was given for it; ValueError when it
    isn't one this input takes. A blank value is the caller's to handle."""
    if spec.type == "date":
        text = str(given).strip()
        if not _is_iso_date(text):
            raise ValueError(f"input {spec.name!r} needs a date like 2026-03-31, not {given!r}")
        return text
    if spec.type == "yes_no":
        answer = _yes_no(given)
        if answer is None:
            raise ValueError(f"input {spec.name!r} needs yes or no, not {given!r}")
        return answer
    if spec.type == "number":
        return _number(spec.name, given)
    if spec.type == "choice":
        wanted = str(given).strip().casefold()
        for option in spec.options:
            if option.strip().casefold() == wanted:
                return option
        raise ValueError(f"input {spec.name!r} is one of {', '.join(spec.options)}, not {given!r}")
    return given


def input_values(specs: Iterable[_Input], given: dict[str, Any], today: date) -> dict[str, Any]:
    """What a run's steps get for each input, from what was given and the defaults on `today`;
    ValueError naming the first input without a value it takes."""
    values: dict[str, Any] = {}
    for spec in specs:
        value = given.get(spec.name, default_value(spec, today))
        if value is not None and value != "":
            values[spec.name] = input_value(spec, value)
        elif spec.required:
            raise ValueError(f"input {spec.name!r} needs a value")
        else:
            values[spec.name] = ""
    return values
