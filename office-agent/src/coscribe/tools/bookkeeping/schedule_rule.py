"""When a scheduled task runs: its rule (a frequency and a time, every few minutes, when a file
arrives in a folder, when something new shows up in a connector, when a program sends it an event,
or by hand) and the next time
that rule comes, in the machine's local wall-clock time (see `scheduled_tasks.py`)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

VALID_KINDS = (
    "manual", "once", "hourly", "daily", "weekdays", "weekly", "monthly", "every", "folder",
    "connector", "webhook",
)  # fmt: skip
# "every": how often a task that checks something may run (decision 0034); "connector": how often
# its tool is asked (decision 0039).
MIN_EVERY_MINUTES = 5
MAX_EVERY_MINUTES = 1440
# "connector" and "webhook": the runs new items or events may start in an hour, unless the task says
# otherwise.
DEFAULT_PER_HOUR = 30
MAX_PER_HOUR = 120


def _to_local_naive(value: datetime) -> datetime:
    """Normalizes any datetime (naive or tz-aware) to a naive local
    wall-clock datetime, so every comparison in this module is apples to
    apples regardless of what a caller passed in."""
    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
    return value


def _parse_local(value: str) -> datetime:
    return _to_local_naive(datetime.fromisoformat(value))


def _parse_hhmm(value: str) -> tuple[int, int]:
    try:
        hour_str, minute_str = value.split(":")
        hour, minute = int(hour_str), int(minute_str)
    except ValueError as exc:
        raise ValueError(f'at must be "HH:MM" for a recurring schedule, got {value!r}') from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f'at must be "HH:MM" (00:00-23:59), got {value!r}')
    return hour, minute


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def _clamp_day(year: int, month: int, day: int) -> int:
    return min(day, calendar.monthrange(year, month)[1])


@dataclass
class ScheduleRule:
    kind: str  # "manual" | "once" | "hourly" | "daily" | "weekdays" |
    # "weekly" | "monthly" -- plain str rather than Literal: aisuite's
    # schema inference has broken on exotic annotations before. "once" predates the six-value
    # Manual/Hourly/Daily/Weekdays/Weekly/Monthly frequency picker the
    # frontend now offers for new tasks -- kept valid here so an
    # already-created "once" trigger keeps working, not exposed as a
    # creatable choice going forward.
    at: str  # "once": a full ISO-8601 timestamp. "manual": unused, may be
    # "". "hourly": "HH:MM" but only the minute is used (fires every hour
    # at that minute; the hour is ignored). Otherwise: "HH:MM".
    weekday: int | None = None  # 0=Monday..6=Sunday, required for "weekly"
    day_of_month: int | None = None  # 1-31, required for "monthly" --
    # clamped to a given month's real last day if it doesn't have that many.
    start_date: str | None = None  # "YYYY-MM-DD" -- the schedule produces
    # no occurrence before this date; None means "starting now." Unused
    # (and meaningless) for "manual"/"once"/"folder".
    minutes: int | None = None  # "every": runs this many minutes apart.
    # "folder": each new file in `folder` matching `pattern` ("*.pdf") starts a run with its path
    # as the workflow's file input `input`; it has no next_run_at, the poll looks at the folder.
    folder: str | None = None
    pattern: str = "*"
    input: str | None = None
    # "connector" (decision 0039): every `minutes`, a connector's `tool` is called with `args`, and
    # each new item in its answer starts a run. `inputs_from` maps an input to the item's field
    # ("sender.email"), "*" the whole item, "" the input's default; an input not named takes the
    # field of its own name. `trust_unmarked`: the person confirmed a tool its connector doesn't
    # mark read-only. "webhook" (decision 0040): each event a program sends starts a run, its
    # inputs filled as an item's are, within `per_hour`.
    tool: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    inputs_from: dict[str, str] = field(default_factory=dict)
    per_hour: int = DEFAULT_PER_HOUR
    trust_unmarked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "at": self.at,
            "weekday": self.weekday,
            "day_of_month": self.day_of_month,
            "start_date": self.start_date,
            "minutes": self.minutes,
            "folder": self.folder,
            "pattern": self.pattern,
            "input": self.input,
            "tool": self.tool,
            "args": self.args,
            "inputs_from": self.inputs_from,
            "per_hour": self.per_hour,
            "trust_unmarked": self.trust_unmarked,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduleRule:
        return cls(
            kind=data["kind"],
            at=data["at"],
            weekday=data.get("weekday"),
            day_of_month=data.get("day_of_month"),
            start_date=data.get("start_date"),
            minutes=data.get("minutes"),
            folder=data.get("folder"),
            pattern=data.get("pattern") or "*",
            input=data.get("input"),
            tool=data.get("tool"),
            args=dict(data.get("args") or {}),
            inputs_from={str(k): str(v) for k, v in (data.get("inputs_from") or {}).items()},
            per_hour=int(data.get("per_hour") or DEFAULT_PER_HOUR),
            trust_unmarked=bool(data.get("trust_unmarked", False)),
        )


def compute_next_run_at(rule: ScheduleRule, after: datetime) -> str | None:
    """The next real occurrence strictly after `after`, as a naive local
    ISO string. None for a "manual" rule (never fires on its own -- only
    via an explicit run-now), for a "folder" or "webhook" rule (a new file or an event starts it),
    and for a "once" rule whose `at` is already in the past -- create_trigger
    rejects the latter case up front (same "reject a past timestamp" posture
    sleep_until already has); pause/resume_scheduled_task never re-run
    this against a "once" rule that already fired (it disables itself
    instead, see poll_due_scheduled_tasks).

    `rule.start_date`, if set, floors the search: no occurrence before
    that date is ever returned, by raising the effective `after` to just
    before start_date's own start-of-day when that's later than the real
    `after` -- a no-op once the schedule's actual occurrences have caught
    up to or passed start_date."""
    after = _to_local_naive(after)
    if rule.kind in ("manual", "folder", "webhook"):
        return None
    if rule.start_date is not None:
        floor = datetime.fromisoformat(rule.start_date) - timedelta(microseconds=1)
        if floor > after:
            after = floor
    if rule.kind == "once":
        candidate = _parse_local(rule.at)
        return candidate.isoformat() if candidate > after else None

    if rule.kind in ("every", "connector"):
        return _every(rule, after)
    return _next_by_clock(rule, after)


def _every(rule: ScheduleRule, after: datetime) -> str:
    minutes = rule.minutes or 0
    if not MIN_EVERY_MINUTES <= minutes <= MAX_EVERY_MINUTES:
        raise ValueError(
            f"minutes must be {MIN_EVERY_MINUTES}-{MAX_EVERY_MINUTES} for {rule.kind!r}"
        )
    return (after.replace(second=0, microsecond=0) + timedelta(minutes=minutes)).isoformat()


def _next_by_clock(rule: ScheduleRule, after: datetime) -> str:
    """The hourly, daily, weekday, weekly and monthly kinds: the next time at `rule.at`."""
    hour, minute = _parse_hhmm(rule.at)

    if rule.kind == "hourly":
        # Only the minute matters -- fires every hour at that minute,
        # regardless of what hour `at` itself names.
        candidate = after.replace(minute=minute, second=0, microsecond=0)
        if candidate <= after:
            candidate += timedelta(hours=1)
        return candidate.isoformat()

    if rule.kind == "daily":
        candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= after:
            candidate += timedelta(days=1)
        return candidate.isoformat()

    if rule.kind == "weekdays":
        candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= after:
            candidate += timedelta(days=1)
        while candidate.weekday() >= 5:  # 5=Saturday, 6=Sunday
            candidate += timedelta(days=1)
        return candidate.isoformat()

    if rule.kind == "weekly":
        if rule.weekday is None or not (0 <= rule.weekday <= 6):
            raise ValueError('weekday (0=Monday..6=Sunday) is required for a "weekly" schedule')
        candidate = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (rule.weekday - candidate.weekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= after:
            candidate += timedelta(days=7)
        return candidate.isoformat()

    if rule.kind == "monthly":
        if rule.day_of_month is None or not (1 <= rule.day_of_month <= 31):
            raise ValueError('day_of_month (1-31) is required for a "monthly" schedule')
        year, month = after.year, after.month
        day = _clamp_day(year, month, rule.day_of_month)
        candidate = after.replace(
            year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0
        )
        if candidate <= after:
            year, month = _add_months(year, month, 1)
            day = _clamp_day(year, month, rule.day_of_month)
            candidate = candidate.replace(year=year, month=month, day=day)
        return candidate.isoformat()

    raise ValueError(f"Unknown schedule kind {rule.kind!r}, expected one of {VALID_KINDS}")
