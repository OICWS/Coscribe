"""The items a "connector" task has already started runs for (decision 0039), so each new item in
its tool's answer starts one run, and what those items fill in. One JSON file per task next to its
memory: what was asked (the tool and its arguments), the keys of the items seen, the latest
check, and the items that started no run and why.

The first look takes what is there as seen, as a folder task does with its files. An item is
known by a field like `id`; one without is known by a fingerprint of all of it, so an item that
changes is new again. Keys are kept even when an item leaves the answer: an answer that comes
back short once (a slow server, a page of results) must not make every item new."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...workflow_spec import WorkflowInput, input_values
from ._trigger_files import trigger_file

if TYPE_CHECKING:
    from .schedule_rule import ScheduleRule
    from .scheduled_run import ScheduledRun

# Runs a task's items may have going at once, so also the most a check starts; the rest wait for
# the next checks.
MAX_RUNNING = 3
# An item bigger than this starts no run: steps would read it whole.
MAX_ITEM_CHARS = 64_000
# Enough to cover the longest answer a connector gives, so an item scrolled out of one never
# comes back as new.
_MAX_KEYS = 2_000
_MAX_MISSED = 20

# The fields a service names an item by, first match wins.
_KEY_FIELDS = ("id", "messageId", "message_id", "uuid", "key", "url", "link", "href")
# Where a service puts the list in an answer that is an object.
_LIST_FIELDS = (
    "items", "results", "messages", "data", "issues", "pages", "records", "rows", "entries",
    "files", "events", "value", "threads", "tasks",
)  # fmt: skip
# The fields that say what an item is, for the line naming it.
_TITLE_FIELDS = ("title", "subject", "name", "summary", "snippet")
WHOLE_ITEM = "*"


def items_of(answer: Any) -> list[Any] | None:
    """The list in a tool's answer: the answer itself, or the list an object holds. None when
    there is none, so a check can say the tool doesn't answer with a list."""
    if isinstance(answer, list):
        return answer
    if not isinstance(answer, dict):
        return None
    for name in _LIST_FIELDS:
        if isinstance(answer.get(name), list):
            return list(answer[name])
    lists = [value for value in answer.values() if isinstance(value, list)]
    return lists[0] if len(lists) == 1 else None


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def item_key(item: Any) -> str:
    if isinstance(item, dict):
        for name in _KEY_FIELDS:
            value = item.get(name)
            if isinstance(value, (str, int)) and not isinstance(value, bool) and value != "":
                return f"{name}:{value}"
    return "sha:" + hashlib.sha256(_canonical(item).encode()).hexdigest()[:24]


def item_title(item: Any) -> str:
    if isinstance(item, dict):
        for name in _TITLE_FIELDS:
            text = item.get(name)
            if isinstance(text, str) and text.strip():
                return text.strip()[:80]
    if isinstance(item, str):
        return item.strip()[:80]
    return item_key(item)


def item_fields(item: Any, prefix: str = "", depth: int = 0) -> dict[str, Any]:
    """Each field of an item that is a value, by its dotted path ("sender.email"). A list is one
    field, as an input takes it whole."""
    if not isinstance(item, dict) or depth > 3:
        return {}
    fields: dict[str, Any] = {}
    for name, value in item.items():
        path = f"{prefix}{name}"
        if isinstance(value, dict):
            fields |= item_fields(value, f"{path}.", depth + 1)
        else:
            fields[path] = value
    return fields


def _plain(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def _field(item: Any, path: str) -> Any:
    current = item
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _matching_field(spec: WorkflowInput, fields: dict[str, Any]) -> str:
    """The field an input takes when the person didn't pick one: the one named like it."""
    wanted = {_plain(spec.name), _plain(spec.label)} - {""}
    for path in fields:
        if _plain(path) in wanted or _plain(path.rsplit(".", 1)[-1]) in wanted:
            return path
    return ""


def event_inputs(
    specs: Iterable[WorkflowInput], inputs_from: dict[str, str], item: Any, today: date
) -> dict[str, Any]:
    """The inputs a run started by `item` gets, checked against each input's type; ValueError
    saying, in the person's words, why the item can't start a run."""
    specs = list(specs)
    fields = item_fields(item)
    given: dict[str, Any] = {}
    for spec in specs:
        path = inputs_from[spec.name] if spec.name in inputs_from else _matching_field(spec, fields)
        if not path:
            continue
        value = item if path == WHOLE_ITEM else _field(item, path)
        if isinstance(value, (dict, list)):
            if spec.type != "text":
                label = spec.label or spec.name
                raise ValueError(f"{label} takes one value, and {path} holds more")
            value = json.dumps(value, ensure_ascii=False, indent=2)
        if value is not None:
            given[spec.name] = value
    try:
        return input_values(specs, given, today)
    except ValueError as exc:
        labels = {f"input {s.name!r}": s.label or s.name for s in specs}
        message = str(exc)
        for named, label in labels.items():
            message = message.replace(named, label)
        raise ValueError(message[:1].upper() + message[1:]) from exc


def oversized(item: Any) -> bool:
    return len(_canonical(item)) > MAX_ITEM_CHARS


def room(runs: Iterable[ScheduledRun], per_hour: int, now: datetime) -> int:
    """How many runs new items may start now: within the hour's limit, beside the ones going."""
    hour_ago = (now - timedelta(hours=1)).isoformat()
    mine = [run for run in runs if run.source == "connector"]
    in_hour = sum(run.started_at >= hour_ago for run in mine)
    going = sum(run.status == "running" for run in mine)
    return max(0, min(per_hour - in_hour, MAX_RUNNING - going))


def _missed(item: Any, reason: str) -> dict[str, str]:
    return {"at": datetime.now().isoformat(timespec="seconds"), "item": item_title(item),
            "reason": reason}  # fmt: skip


class ConnectorItems:
    def __init__(self, state_dir: str | Path) -> None:
        self.root = Path(state_dir) / "task_memory"

    def unseen(self, trigger_id: str, asked: Any, items: list[Any]) -> list[tuple[str, Any]] | None:
        """The items not seen yet, in the answer's order, each with its key; None on the first look
        at what `asked` names (a tool and its arguments), which takes them all as seen."""
        state = self.read(trigger_id)
        keys = [(item_key(item), item) for item in items]
        if state.get("asked") != asked:
            # A task that asks something else starts over, as a folder task does on a new folder.
            self._write(trigger_id, {"asked": asked, "seen": [k for k, _ in keys][-_MAX_KEYS:]})
            return None
        seen = set(state.get("seen") or [])
        fresh: list[tuple[str, Any]] = []
        for key, item in keys:
            if key not in seen:
                seen.add(key)
                fresh.append((key, item))
        return fresh

    @staticmethod
    def preview(answer: Any, shown: int) -> dict[str, Any] | None:
        """What the task form shows of an answer: how many items, the first `shown`, and each
        field of those that is a value with an example. None when the answer isn't a list."""
        items = items_of(answer)
        if items is None:
            return None
        fields: dict[str, Any] = {}
        for item in items[:shown]:
            fields = {**item_fields(item), **fields}
        listed = [{"title": item_title(item), "item": item} for item in items[:shown]]
        return {"count": len(items), "items": listed, "fields": fields}

    def take(
        self,
        trigger_id: str,
        rule: ScheduleRule,
        specs: list[WorkflowInput],
        runs: list[ScheduledRun],
        answer: Any,
    ) -> tuple[list[tuple[str, Any, dict[str, Any]]], str]:
        """The runs a check's `answer` starts, as each item's key, the item and its inputs, and
        what the check found, in a line for the audit log. An item that can't start a run is
        recorded with the reason and never tried again; one over the limits waits for a later
        check."""
        items = items_of(answer)
        if items is None:
            error = "Its answer isn't a list of items"
            self.checked(trigger_id, error=error)
            return [], error
        fresh = self.unseen(trigger_id, {"tool": rule.tool, "args": rule.args}, items)
        if fresh is None:
            self.checked(trigger_id)
            return [], f"First look: {len(items)} items taken as seen"
        free = room(runs, rule.per_hour, datetime.now())
        starting: list[tuple[str, Any, dict[str, Any]]] = []
        taken: list[str] = []
        missed: list[dict[str, str]] = []
        for key, item in fresh:
            try:
                if oversized(item):
                    raise ValueError(f"It is over {MAX_ITEM_CHARS // 1000} KB")
                inputs = event_inputs(specs, rule.inputs_from, item, date.today())
            except ValueError as exc:
                missed.append(_missed(item, str(exc)))
                taken.append(key)
                continue
            if len(starting) < free:
                starting.append((key, item, inputs))
                taken.append(key)
        held = len(fresh) - len(taken)
        self.checked(trigger_id, taken=taken, missed=missed, found=len(fresh), held=held)
        if not fresh:
            return [], ""
        return starting, (
            f"{len(fresh)} new: {len(starting)} started, {len(missed)} refused, {held} held"
        )

    def checked(
        self,
        trigger_id: str,
        *,
        taken: Iterable[str] = (),
        missed: Iterable[dict[str, str]] = (),
        found: int = 0,
        held: int = 0,
        error: str | None = None,
    ) -> None:
        """Record a check: the keys it took (started or refused, never asked about again), the items
        it refused and why, and how it went."""
        state = self.read(trigger_id)
        state["seen"] = [*(state.get("seen") or []), *taken][-_MAX_KEYS:]
        state["missed"] = [*(state.get("missed") or []), *missed][-_MAX_MISSED:]
        state["last_check"] = {
            "at": datetime.now().isoformat(timespec="seconds"),
            "found": found,
            "held": held,
            "error": error,
        }
        self._write(trigger_id, state)

    def shown(self, trigger_id: str) -> dict[str, Any]:
        """What the task page shows: the latest check and the items that started no run."""
        state = self.read(trigger_id)
        return {"last_check": state.get("last_check"), "missed": state.get("missed") or []}

    def forget(self, trigger_id: str) -> None:
        self._path(trigger_id).unlink(missing_ok=True)

    def read(self, trigger_id: str) -> dict[str, Any]:
        try:
            data = json.loads(self._path(trigger_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, trigger_id: str, state: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(trigger_id)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, path)

    def _path(self, trigger_id: str) -> Path:
        return trigger_file(self.root, trigger_id, ".connector.json")
