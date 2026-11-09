"""The steps that stop a run until something outside it happens: an approval or an ask step waits
for a person, a wait step for a time or a file (decision 0033).

Each pauses with interrupt(), and LangGraph runs the whole node again from its start when the run
resumes, so nothing before an interrupt does more than record the step. An ask or wait step first
settles when its pause ends, in a graph step of its own that loops back to the node: the resumed
node then reads the deadline it paused on, not one worked out again on resume."""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from langgraph.errors import GraphBubbleUp
from langgraph.types import interrupt

from ..workflow_spec import (
    RELATIVE_DATES,
    ApprovalStep,
    AskField,
    AskStep,
    Step,
    WaitStep,
    conditions_hold,
    default_value,
    input_value,
    render_text,
    resolve,
    resolve_date,
)
from .step_work import StepContext, StepFailed, StepRecord, checks_of, now_text, preview

# The route an ask or wait step takes back into itself once it has settled its deadline.
# The note on an ask step that went on without an answer, which the run's report lists.
NO_ANSWER = "No one answered: went on with the defaults"
PAUSED = "pause"
# A file counts as there once it has stopped changing for this long: one still being written,
# or copied in, would be read half-done.
FILE_SETTLE_SECONDS = 5.0
_PICK_LABEL_CHARS = 120


def clock() -> datetime:
    """Now; the tests set the time through this."""
    return datetime.now()


class _Builder(Protocol):
    ctx: StepContext

    async def emit(self, record: StepRecord) -> None: ...

    async def recover(
        self, step: Step, state: Any, it: list[int], started: str, tries: int, exc: Exception
    ) -> dict[str, Any]: ...


def _day(on: str, values: dict[str, Any], today: date) -> date:
    """The day `on` names: a relative one, a date, a reference or a text with references."""
    if on in RELATIVE_DATES:
        return date.fromisoformat(resolve_date(on, today))
    if "{{" in on:
        text = render_text(on, values)
    else:
        text = on if on[:1].isdigit() else str(resolve(on, values))
    try:
        return date.fromisoformat(text.strip()[:10])
    except ValueError as exc:
        raise StepFailed(f"{text!r} isn't a date to wait for") from exc


def wait_ends(step: WaitStep, values: dict[str, Any], now: datetime) -> datetime:
    """When a wait step stops waiting: its time, or for a file the longest it waits."""
    if step.until == "duration":
        return now + timedelta(minutes=step.minutes or 0)
    if step.until == "file":
        return now + timedelta(minutes=step.max_minutes)
    hour, minute = (int(part) for part in (step.at or "00:00").split(":"))
    if step.on is not None:
        return datetime.combine(_day(step.on, values, now.date()), datetime.min.time()).replace(
            hour=hour, minute=minute
        )
    at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return at if at > now else at + timedelta(days=1)


def waited_path(step: WaitStep, values: dict[str, Any], root: Path) -> Path:
    path = Path(render_text(step.path or "", values)).expanduser()
    return path if path.is_absolute() else root / path


def file_ready(path: Path) -> bool:
    """The file is there and has stopped changing."""
    try:
        changed = path.stat().st_mtime
    except OSError:
        return False
    return path.is_file() and time.time() - changed >= FILE_SETTLE_SECONDS


def _pick_label(item: Any, show: str) -> str:
    shown = item.get(show) if show and isinstance(item, dict) else item
    text = shown if isinstance(shown, str) else str(preview(shown))
    return text if len(text) <= _PICK_LABEL_CHARS else f"{text[: _PICK_LABEL_CHARS - 1]}…"


def _pick_items(field: AskField, values: dict[str, Any]) -> list[Any]:
    items = resolve(field.items or "", values)
    if not isinstance(items, list):
        raise StepFailed(f"{field.items!r} isn't a list to pick from")
    return items


def ask_fields(step: AskStep, values: dict[str, Any], today: date) -> list[dict[str, Any]]:
    """What the person is asked, with each default as this run has it and a pick's items."""
    fields = []
    for field in step.fields:
        shown: dict[str, Any] = {
            "name": field.name, "label": field.label or field.name, "type": field.type,
            "options": field.options, "required": field.required,
            "default": None if field.type == "pick" else default_value(field, today),
        }  # fmt: skip
        if field.type == "pick":
            items = _pick_items(field, values)
            shown["items"] = [{"label": _pick_label(item, field.show), "index": index}
                              for index, item in enumerate(items)]  # fmt: skip
        fields.append(shown)
    return fields


def ask_answers(
    step: AskStep, given: dict[str, Any], values: dict[str, Any], today: date
) -> dict[str, Any]:
    """What the later steps read from the person's answers: each value as its kind takes it, a
    pick's places as the items picked. ValueError names the first that doesn't fit."""
    answers: dict[str, Any] = {}
    for field in step.fields:
        value = given.get(field.name)
        if field.type == "pick":
            items = _pick_items(field, values)
            places = value if isinstance(value, list) else []
            if any(not isinstance(i, int) or not 0 <= i < len(items) for i in places):
                raise ValueError(f"{field.label or field.name}: pick from the list shown")
            if field.required and not places:
                raise ValueError(f"{field.label or field.name}: pick at least one")
            answers[field.name] = [items[i] for i in sorted(set(places))]
        elif value is None or value == "":
            if field.required:
                raise ValueError(f"{field.label or field.name} needs a value")
            answers[field.name] = ""
        else:
            answers[field.name] = input_value(field, value)
    return answers


def ask_defaults(step: AskStep, values: dict[str, Any], today: date) -> dict[str, Any]:
    given = {f.name: [] if f.type == "pick" else default_value(f, today) for f in step.fields}
    return ask_answers(step, given, values, today)


class Pauses:
    """Runs the steps that pause the run, for the graph builder that owns them."""

    def __init__(self, builder: _Builder) -> None:
        self.builder = builder

    async def _pause(
        self, step: Step, request: dict[str, Any], record: StepRecord
    ) -> dict[str, Any]:
        """Wait for an answer; the step shows as waiting only when the run really stops here,
        not when the resume replays the answer."""
        try:
            answer = interrupt({"step_id": step.id, "title": step.title, **request})
        except GraphBubbleUp:
            await self.builder.emit(record)
            raise
        return answer if isinstance(answer, dict) else {}

    async def approval(
        self, step: ApprovalStep, values: dict[str, Any], it: list[int]
    ) -> dict[str, Any]:
        started = now_text()
        checks = None
        if step.when:
            held, checked = conditions_hold(step.when, step.match, values)
            checks = checks_of(checked)
            if not held:
                await self.builder.emit(StepRecord(step.id, "skipped", started, now_text(),
                                                   checks=checks, iteration=it))  # fmt: skip
                return {"values": {}}
        message = render_text(step.message, values)
        waiting = StepRecord(step.id, "waiting", started, output=message, checks=checks,
                             iteration=it)  # fmt: skip
        answer = await self._pause(step, {"message": message}, waiting)
        note = str(answer.get("note") or "")
        if answer.get("approved") is not True:
            error = "Not approved" + (f": {note}" if note else "")
            await self.builder.emit(StepRecord(step.id, "failed", started, now_text(),
                                               output=message, error=error, note=note or None,
                                               iteration=it))  # fmt: skip
            raise StepFailed(error, step_id=step.id, declined=True)
        await self.builder.emit(StepRecord(step.id, "done", started, now_text(), output=message,
                                           note=note or None, iteration=it))  # fmt: skip
        return {"values": {}}

    async def settle(
        self, step: AskStep | WaitStep, values: dict[str, Any], it: list[int]
    ) -> dict[str, Any]:
        """The step's first graph step in a pass: when its pause ends, and for a file where it
        looks, kept in state for the pause and its resume."""
        started = now_text()
        now = clock()
        held: dict[str, Any] = {"route": PAUSED, "started": started, "until": None}
        if isinstance(step, WaitStep):
            held["until"] = wait_ends(step, values, now).isoformat(timespec="seconds")
            if step.until == "file":
                held["path"] = str(waited_path(step, values, self.builder.ctx.workspace_root))
        elif step.timeout_hours is not None:
            ends = now + timedelta(hours=step.timeout_hours)
            held["until"] = ends.isoformat(timespec="seconds")
        await self.builder.emit(StepRecord(step.id, "running", started, iteration=it))
        return {"attempts": {step.id: held}}

    async def ask(
        self, step: AskStep, values: dict[str, Any], held: dict[str, Any], it: list[int]
    ) -> dict[str, Any]:
        started, until = held["started"], held["until"]
        today = clock().date()
        message = render_text(step.message, values)
        pause = {"kind": "ask", "until": until, "fields": ask_fields(step, values, today),
                 "on_timeout": step.on_timeout}  # fmt: skip
        # A test run has no one to answer: it goes on with the defaults where every value that
        # must be given has one, and otherwise stops here as it would before an approval.
        if not self.builder.ctx.waits and not any(
            f.required and f.default in (None, "") for f in step.fields
        ):
            answers = ask_defaults(step, values, today)
            await self.builder.emit(StepRecord(step.id, "done", started, now_text(),
                                               output=preview(answers),
                                               note="A test run: went on with the defaults",
                                               iteration=it))  # fmt: skip
            return {"values": {step.save_as: answers}, "attempts": {step.id: {"route": "ok"}}}
        # Answers that didn't fit are asked for again, saying why.
        waiting = StepRecord(step.id, "waiting", started, output=message, iteration=it,
                             error=held.get("problem"), pause=pause)  # fmt: skip
        answer = await self._pause(step, {"message": message, "pause": pause}, waiting)
        if answer.get("woke"):
            if until is None or clock() < datetime.fromisoformat(until):
                return {"attempts": {step.id: held}}
            if step.on_timeout == "fail":
                raise await self._failed(step, started, it, "No one answered in time", message)
            answers = ask_defaults(step, values, today)
            note = NO_ANSWER
        elif answer.get("approved") is not True:
            raise await self._failed(step, started, it, "Stopped: you chose not to answer", message,
                                     declined=True)  # fmt: skip
        else:
            try:
                answers = ask_answers(step, answer.get("values") or {}, values, today)
            except ValueError as exc:
                return {"attempts": {step.id: {**held, "problem": str(exc)}}}
            note = ""
        await self.builder.emit(StepRecord(step.id, "done", started, now_text(),
                                           output=preview(answers), note=note or None,
                                           iteration=it))  # fmt: skip
        return {"values": {step.save_as: answers}, "attempts": {step.id: {"route": "ok"}}}

    async def wait(
        self, step: WaitStep, state: Any, held: dict[str, Any], it: list[int]
    ) -> dict[str, Any]:
        started, until = held["started"], datetime.fromisoformat(held["until"])
        path = Path(held["path"]) if held.get("path") else None
        # A test run doesn't wait: it looks for the file once.
        over = not self.builder.ctx.waits
        if path is not None and file_ready(path):
            return await self._waited(step, started, it, path)
        if path is None and (over or clock() >= until):
            return await self._waited(step, started, it, None)
        if over:
            return await self._missing(step, state, it, held, path)
        pause = {"kind": "wait", "until": held["until"], **({"path": str(path)} if path else {})}
        waiting = StepRecord(step.id, "waiting", started, iteration=it, pause=pause)
        answer = await self._pause(step, {"message": step.title, "pause": pause}, waiting)
        if path is None and answer.get("approved") is True:
            return await self._waited(step, started, it, None)
        if path is not None and file_ready(path):
            return await self._waited(step, started, it, path)
        if clock() < until:
            return {"attempts": {step.id: held}}
        return await self._missing(step, state, it, held, path)

    async def _missing(
        self, step: WaitStep, state: Any, it: list[int], held: dict[str, Any], path: Path | None
    ) -> dict[str, Any]:
        """The file didn't come in time: go on without it, or fail the step."""
        if path is not None and step.if_missing == "continue":
            return await self._waited(step, held["started"], it, path, found=False)
        missing = StepFailed(f"{path} didn't appear in time")
        return await self.builder.recover(step, state, it, held["started"], 1, missing)

    async def _waited(
        self, step: WaitStep, started: str, it: list[int], path: Path | None, found: bool = True
    ) -> dict[str, Any]:
        result = {"path": str(path), "found": found} if path is not None else None
        await self.builder.emit(StepRecord(step.id, "done", started, now_text(), output=result,
                                           iteration=it))  # fmt: skip
        made = {step.save_as: result} if step.save_as else {}
        return {"values": made, "attempts": {step.id: {"route": "ok"}}}

    async def _failed(
        self, step: Step, started: str, it: list[int], error: str, message: str,
        declined: bool = False,
    ) -> StepFailed:  # fmt: skip
        await self.builder.emit(StepRecord(step.id, "failed", started, now_text(), output=message,
                                           error=error, iteration=it))  # fmt: skip
        return StepFailed(error, step_id=step.id, declined=declined)


def paused_at(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    """What a stopped run's ask or wait step, or its question about tokens, waits for (its
    record's `pause`), if one does."""
    waiting = next((r for r in reversed(records) if r.get("status") == "waiting"), None)
    pause = waiting.get("pause") if waiting else None
    return pause if isinstance(pause, dict) else None


def wake_due(pause: dict[str, Any], now: datetime) -> bool:
    """The run should go on: its wait's time came or its file appeared, or no one answered its
    ask step in time."""
    if pause.get("path") and file_ready(Path(pause["path"])):
        return True
    until = pause.get("until")
    return isinstance(until, str) and now >= datetime.fromisoformat(until)


def answer_problem(step: Step, given: dict[str, Any]) -> str | None:
    """Why answers to an ask step won't do, as far as they can be checked without the run's
    values (a pick's items are checked when the run goes on); None when they will."""
    if not isinstance(step, AskStep):
        return None
    for field in step.fields:
        value = given.get(field.name)
        blank = value is None or value == "" or value == []
        if blank and field.required:
            return f"{field.label or field.name} needs a value"
        if not blank and field.type != "pick":
            try:
                input_value(field, value)
            except ValueError as exc:
                return str(exc)
    return None
