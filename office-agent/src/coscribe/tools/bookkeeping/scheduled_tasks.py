"""Scheduled tasks: global, named and persisted, made in a conversation (create_scheduled_task)
or on the Scheduled page -- unlike tools/bookkeeping/selfwake.py's one-off, thread-scoped pauses.
This module holds the triggers, their store and the model's tools; firing a due one needs a live
session and lives in runtime_lg/scheduled_tasks.py. ARCHITECTURE.md's "Repeated work becomes
fixed steps" has the reasoning. Times ("HH:MM") are the server's local wall clock, as with cron:
the app is single-user and local-first."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from ...runtime import DEFAULT_ENVIRONMENT, Environments, tool_metadata
from ...workflow_spec import current_shape, parse_workflow, workflow_error
from ._trigger_files import is_trigger_id, trigger_file
from .connector_items import ConnectorItems
from .folder_watch import FolderWatch
from .schedule_rule import (
    DEFAULT_PER_HOUR,
    MAX_PER_HOUR,
    VALID_KINDS,
    ScheduleRule,
    _to_local_naive,
    compute_next_run_at,
)
from .scheduled_run import ScheduledRun, fold_quiet
from .task_calls import TaskCalls, check_calls
from .task_memory import TaskMemory
from .task_versions import TaskVersions

VALID_APPROVAL_MODES = ("manual", "auto", "skip")
RUN_STATUSES = ("running", "completed", "failed", "needs_approval", "waiting", "stopped")

# Every run's conversation is keyed off this prefix (see run_thread_id) --
# shared with web/app.py's list_threads, which filters by it so run
# conversations only ever show up under Scheduled, never in the ordinary
# chat sidebar.
SCHEDULED_THREAD_PREFIX = "scheduled-"

# Respond-only interrupt tools (like ask_user_question): the model's call
# becomes a draft the user reviews and edits in the UI, and whatever they
# decide is substituted as the tool's result -- the Python body below only
# ever runs outside such a graph (e.g. a direct call in tests).
TASK_DRAFT_TOOL_NAMES: frozenset[str] = frozenset({"create_scheduled_task", "edit_scheduled_task"})

# edit_scheduled_task's fields, as the draft the user reviews names them.
_EDITABLE_FIELDS = tuple(
    "name kind at prompt weekday day_of_month start_date model approval_mode".split()
)

# What a task that starts by itself is told in `watch`, and keeps on its rule.
_WATCH_FIELDS = tuple(
    "minutes folder pattern input tool args inputs_from per_hour trust_unmarked".split()
)

# What a run records besides its steps and status.
_EVIDENCE = frozenset(
    "screenshot page files sites investigation queued quiet versions called".split()
)

# Oldest run records beyond this are dropped from the trigger (their
# conversations are deleted along with them, see web/app.py).
MAX_RUNS_KEPT = 50
# The notes a run carries forward are part of every future run's prompt,
# so they're kept deliberately small.
MAX_NOTES_CHARS = 4000


def run_thread_id(trigger_id: str, run_id: str) -> str:
    return f"{SCHEDULED_THREAD_PREFIX}{trigger_id}-{run_id}"


def parse_run_thread_id(thread_id: str) -> tuple[str, str] | None:
    """(trigger_id, run_id) for a run's own thread, None for anything else
    -- including a pre-per-run trigger's single shared thread
    ("scheduled-<trigger_id>", no run part)."""
    if not thread_id.startswith(SCHEDULED_THREAD_PREFIX):
        return None
    # rpartition: a run_id never contains "-", a trigger_id might.
    trigger_id, sep, run_id = thread_id[len(SCHEDULED_THREAD_PREFIX) :].rpartition("-")
    if not sep or not trigger_id or not run_id:
        return None
    return trigger_id, run_id


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class ScheduledTrigger:
    trigger_id: str
    name: str
    schedule: ScheduleRule
    enabled: bool
    created_at: str
    next_run_at: str | None  # None once a "once" trigger fired, and always for "manual"
    prompt: str = ""
    last_run_at: str | None = None
    last_run_status: str | None = None  # "completed" | "failed" | "stopped"
    # "provider:model"; None is the app's configured default model.
    model: str | None = None
    # One of VALID_APPROVAL_MODES. "manual" is how triggers saved before this field ran, so
    # loading one without it must not change its behavior.
    approval_mode: str = "manual"
    notes_enabled: bool = True
    runs: list[ScheduledRun] = field(default_factory=list)  # oldest first
    # A workflow_spec Workflow as JSON: when set, a run executes these
    # steps instead of handing `prompt` to the model.
    workflow: dict[str, Any] | None = None
    # The environment a run works in: its folders, network, secrets and what may run.
    environment: str = DEFAULT_ENVIRONMENT
    # A task's folder from before environments, until the startup migration moves it into one.
    legacy_workspace: str | None = None
    # The conversation drafts (draft_workflow/revise_workflow ids) saved
    # into this task, so a conversation can show a draft as saved.
    drafts: list[str] = field(default_factory=list)
    # The conversation the task was saved from, if any.
    source_thread: str | None = None
    # After a failed run, open a conversation that looks into it.
    auto_investigate: bool = False
    # What a run was allowed while it waited, beyond what the workflow's
    # steps name themselves: {"folders": [...], "sites": [...]}.
    permissions: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "name": self.name,
            "schedule": self.schedule.to_dict(),
            "enabled": self.enabled,
            "created_at": self.created_at,
            "next_run_at": self.next_run_at,
            "prompt": self.prompt,
            "last_run_at": self.last_run_at,
            "last_run_status": self.last_run_status,
            "model": self.model,
            "approval_mode": self.approval_mode,
            "notes_enabled": self.notes_enabled,
            "runs": [run.to_dict() for run in self.runs],
            "workflow": self.workflow,
            "environment": self.environment,
            **({"workspace": self.legacy_workspace} if self.legacy_workspace else {}),
            "drafts": self.drafts,
            "source_thread": self.source_thread,
            "auto_investigate": self.auto_investigate,
            "permissions": self.permissions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledTrigger:
        runs = [ScheduledRun.from_dict(r) for r in data.get("runs", [])]
        if "runs" not in data and data.get("last_run_at") and data.get("thread_id"):
            # A trigger from before per-run conversations ran every time
            # in one shared thread -- surfaced as a single run so its
            # history stays reachable.
            runs = [
                ScheduledRun(
                    run_id="earlier",
                    thread_id=data["thread_id"],
                    started_at=data["last_run_at"],
                    source="scheduled",
                    status=data.get("last_run_status") or "completed",
                    finished_at=data["last_run_at"],
                )
            ]
        return cls(
            trigger_id=data["trigger_id"],
            name=data["name"],
            schedule=ScheduleRule.from_dict(data["schedule"]),
            enabled=data["enabled"],
            created_at=data["created_at"],
            next_run_at=data.get("next_run_at"),
            prompt=data.get("prompt") or "",
            last_run_at=data.get("last_run_at"),
            last_run_status=data.get("last_run_status"),
            model=data.get("model"),
            approval_mode=data.get("approval_mode", "manual"),
            notes_enabled=data.get("notes_enabled", True),
            runs=runs,
            workflow=current_shape(data.get("workflow")),
            environment=data.get("environment") or DEFAULT_ENVIRONMENT,
            legacy_workspace=data.get("workspace"),
            drafts=list(data.get("drafts") or []),
            source_thread=data.get("source_thread"),
            auto_investigate=bool(data.get("auto_investigate", False)),
            permissions={
                str(kind): [str(item) for item in items]
                for kind, items in (data.get("permissions") or {}).items()
            },
        )

    def find_run(self, run_id: str) -> ScheduledRun | None:
        return next((run for run in self.runs if run.run_id == run_id), None)


class ScheduledTriggerStore:
    """One JSON file per trigger id, global by id (not scoped to any one
    thread) -- same atomic tmp+os.replace() write every other *Store in
    this codebase uses."""

    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        self.root = self.state_dir / "scheduled_tasks"
        # What each task keeps between runs and the files its folder watch has seen
        # (decision 0034), kept beside the tasks and deleted with them.
        self.memory = TaskMemory(self.state_dir)
        self.folders = FolderWatch(self.state_dir)
        self.connector_items = ConnectorItems(self.state_dir)
        self.versions = TaskVersions(self.state_dir)
        self.calls = TaskCalls(self)

    def save(self, trigger: ScheduledTrigger) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = trigger_file(self.root, trigger.trigger_id, ".json")
        tmp_path = path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(trigger.to_dict(), handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    def load(self, trigger_id: str) -> ScheduledTrigger | None:
        if not is_trigger_id(trigger_id):
            return None
        path = trigger_file(self.root, trigger_id, ".json")
        if not path.exists():
            return None
        return ScheduledTrigger.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def grant(self, trigger_id: str, kind: str, target: str) -> ScheduledTrigger | None:
        """Allow a task's runs one more folder or site ("folders"/"sites")."""
        trigger = self.load(trigger_id)
        if trigger is None:
            return None
        allowed = trigger.permissions.setdefault(kind, [])
        if target not in allowed:
            allowed.append(target)
            self.save(trigger)
        return trigger

    def list_all(self) -> list[ScheduledTrigger]:
        if not self.root.is_dir():
            return []
        return [
            ScheduledTrigger.from_dict(json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(self.root.glob("*.json"))
        ]

    def list_due(self, now: datetime) -> list[ScheduledTrigger]:
        now_iso = _to_local_naive(now).isoformat()
        return [
            t
            for t in self.list_all()
            if t.enabled and t.next_run_at is not None and t.next_run_at <= now_iso
        ]

    def delete(self, trigger_id: str) -> bool:
        if not is_trigger_id(trigger_id):
            return False
        path = trigger_file(self.root, trigger_id, ".json")
        existed = path.exists()
        path.unlink(missing_ok=True)
        trigger_file(self.root, trigger_id, ".notes.md").unlink(missing_ok=True)
        self.memory.delete(trigger_id)
        self.folders.forget(trigger_id)
        self.connector_items.forget(trigger_id)
        self.versions.delete(trigger_id)
        return existed

    def start_run(
        self,
        trigger_id: str,
        source: str,
        inputs: dict[str, Any] | None = None,
        event: dict[str, Any] | None = None,
    ) -> tuple[ScheduledTrigger, ScheduledRun, list[ScheduledRun]]:
        """Record a new run as "running". Returns the freshly loaded
        trigger, the new run, and any runs dropped for exceeding
        MAX_RUNS_KEPT (oldest first) so the caller can delete their
        conversations too."""
        trigger = self.load(trigger_id)
        if trigger is None:
            raise KeyError(f"No scheduled task with id {trigger_id!r}")
        run_id = uuid.uuid4().hex[:8]
        run = ScheduledRun(
            run_id=run_id,
            thread_id=run_thread_id(trigger_id, run_id),
            started_at=_now_iso(),
            source=source,
            inputs=inputs,
            event=event,
        )
        trigger.runs, pruned = fold_quiet(trigger.runs)
        trigger.runs.append(run)
        pruned += trigger.runs[:-MAX_RUNS_KEPT]
        trigger.runs = trigger.runs[-MAX_RUNS_KEPT:]
        trigger.last_run_at = run.started_at
        trigger.last_run_status = run.status
        self.save(trigger)
        # The run's conversation reaches what its task's environment allows, like any other.
        environments = Environments(self.state_dir)
        if environments.get(trigger.environment) is not None:
            environments.assign(run.thread_id, trigger.environment)
        return trigger, run, pruned

    def finish_run(
        self, trigger_id: str, run_id: str, status: str, error: str | None = None
    ) -> ScheduledTrigger | None:
        """Re-reads the trigger before writing: a run can take minutes, and
        the user may have edited the task meanwhile -- saving the copy
        loaded at start would silently undo that edit."""
        trigger = self.load(trigger_id)
        if trigger is None:
            return None
        run = trigger.find_run(run_id)
        if run is None:
            return trigger
        run.status = status
        run.error = error
        run.finished_at = _now_iso()
        if trigger.runs and trigger.runs[-1] is run:
            trigger.last_run_status = status
        self.save(trigger)
        return trigger

    def record_evidence(self, trigger_id: str, run_id: str, **fields: Any) -> None:
        """Set a run's screenshot, page, files, sites, investigation, queued or quiet flag."""
        trigger = self.load(trigger_id)
        run = trigger.find_run(run_id) if trigger is not None else None
        if trigger is None or run is None:
            return
        for name, value in fields.items():
            if name not in _EVIDENCE:
                raise ValueError(f"{name!r} isn't run evidence")
            setattr(run, name, value)
        self.save(trigger)

    def record_step(self, trigger_id: str, run_id: str, record: dict[str, Any]) -> None:
        """Replace this step's record on the run -- this pass of it, inside
        a loop -- or append it."""
        trigger = self.load(trigger_id)
        run = trigger.find_run(run_id) if trigger is not None else None
        if trigger is None or run is None:
            return
        for index, existing in enumerate(run.steps):
            if existing.get("step_id") == record.get("step_id") and (
                existing.get("iteration") or []
            ) == (record.get("iteration") or []):
                run.steps[index] = record
                break
        else:
            run.steps.append(record)
        self.save(trigger)

    def reopen_run(self, trigger_id: str, run_id: str) -> ScheduledRun:
        """Mark a finished run as running again -- it's being resumed, a
        step retried, or an approval answered."""
        trigger = self.load(trigger_id)
        run = trigger.find_run(run_id) if trigger is not None else None
        if trigger is None or run is None:
            raise KeyError(f"No run {run_id!r} of scheduled task {trigger_id!r}")
        if run.status == "running":
            raise ValueError("This run is still going")
        run.status = "running"
        run.error = None
        run.finished_at = None
        run.queued = False
        run.screenshot = None
        run.page = None
        run.files = []
        if trigger.runs[-1] is run:
            trigger.last_run_status = "running"
        self.save(trigger)
        return run

    def read_notes(self, trigger_id: str) -> str:
        path = trigger_file(self.root, trigger_id, ".notes.md")
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def write_notes(self, trigger_id: str, notes: str) -> None:
        if len(notes) > MAX_NOTES_CHARS:
            raise ValueError(
                f"Notes are {len(notes)} characters, over the {MAX_NOTES_CHARS} limit -- "
                "condense them to what future runs actually need."
            )
        self.root.mkdir(parents=True, exist_ok=True)
        path = trigger_file(self.root, trigger_id, ".notes.md")
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(notes, encoding="utf-8")
        os.replace(tmp_path, path)


def _validate_and_build_schedule(
    *,
    kind: str,
    at: str,
    prompt: str,
    weekday: int | None,
    day_of_month: int | None,
    start_date: str | None,
    approval_mode: str,
    workflow: dict[str, Any] | None = None,
    watch: dict[str, Any] | None = None,
) -> tuple[ScheduleRule, str | None, dict[str, Any] | None]:
    """Shared validation + ScheduleRule construction for create_trigger
    and update_trigger -- kept as one function so the two paths can never
    silently drift out of sync with each other, same reasoning
    create_trigger's own docstring already gives for being shared between
    the model tool and the REST endpoint."""
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {VALID_KINDS}, got {kind!r}")
    if approval_mode not in VALID_APPROVAL_MODES:
        raise ValueError(
            f"approval_mode must be one of {VALID_APPROVAL_MODES}, got {approval_mode!r}"
        )
    normalized_workflow = None
    if workflow is not None:
        try:
            normalized_workflow = parse_workflow(workflow).model_dump(mode="json")
        except ValidationError as exc:
            raise ValueError(f"The workflow isn't valid: {workflow_error(exc, workflow)}") from exc
    elif not prompt.strip():
        raise ValueError("prompt cannot be blank")

    watch = watch or {}
    rule = ScheduleRule(
        kind=kind, at=at, weekday=weekday, day_of_month=day_of_month, start_date=start_date,
        minutes=watch.get("minutes"), folder=watch.get("folder"),
        pattern=watch.get("pattern") or "*", input=watch.get("input"),
    )  # fmt: skip
    if kind == "folder":
        _check_folder_rule(rule, normalized_workflow)
    if kind == "connector":
        _connector_rule(rule, watch, normalized_workflow)
    next_run_at = compute_next_run_at(rule, datetime.now())
    # "manual" and "folder" never have a next_run_at by design (see ScheduleRule.kind) --
    # only every other kind treats a None result as "at was in the past."
    if next_run_at is None and kind not in ("manual", "folder"):
        raise ValueError(f"at must be in the future, got {at!r}")
    return rule, next_run_at, normalized_workflow


def _check_folder_rule(rule: ScheduleRule, workflow: dict[str, Any] | None) -> None:
    folder = Path(rule.folder or "")
    if not rule.folder or not folder.is_absolute() or not folder.is_dir():
        raise ValueError(f"A task that starts on a new file needs a folder, not {rule.folder!r}")
    inputs = {i["name"]: i.get("type") for i in (workflow or {}).get("inputs") or []}
    if inputs.get(rule.input or "") != "file":
        raise ValueError("A task that starts on a new file passes it to one of its file inputs")


def _connector_rule(
    rule: ScheduleRule, watch: dict[str, Any], workflow: dict[str, Any] | None
) -> None:
    """A task started by new items in a connector (decision 0039): its tool, the tool's arguments,
    which input takes which field, and its hourly limit."""
    if workflow is None:
        raise ValueError("Only a task with steps can start on something new in a connector")
    rule.tool = str(watch.get("tool") or "").strip() or None
    if rule.tool is None:
        raise ValueError("A task that starts on something new in a connector names the tool to ask")
    args, inputs_from = watch.get("args") or {}, watch.get("inputs_from") or {}
    if not isinstance(args, dict) or not isinstance(inputs_from, dict):
        raise ValueError("A connector check's arguments and inputs are each a set of names")
    names = {i["name"] for i in workflow.get("inputs") or []}
    unknown = sorted(set(inputs_from) - names)
    if unknown:
        raise ValueError(f"The task has no input {unknown[0]!r} to fill from an item")
    rule.args, rule.inputs_from = args, {str(k): str(v) for k, v in inputs_from.items()}
    rule.per_hour = int(watch.get("per_hour") or DEFAULT_PER_HOUR)
    if not 1 <= rule.per_hour <= MAX_PER_HOUR:
        raise ValueError(f"A task starts 1 to {MAX_PER_HOUR} runs an hour from new items")
    rule.trust_unmarked = bool(watch.get("trust_unmarked", False))


def _watch_folder(trigger: ScheduledTrigger) -> None:
    """A task started by files in a folder may read that folder."""
    folder = trigger.schedule.folder
    allowed = trigger.permissions.setdefault("folders", [])
    if trigger.schedule.kind == "folder" and folder and folder not in allowed:
        allowed.append(folder)


def _checked_environment(store: ScheduledTriggerStore, environment: str | None) -> str:
    if not environment:
        return DEFAULT_ENVIRONMENT
    if Environments(store.state_dir).get(environment) is None:
        raise ValueError(f"There is no environment {environment!r}")
    return environment


def create_trigger(
    store: ScheduledTriggerStore,
    *,
    name: str,
    kind: str,
    at: str,
    prompt: str,
    weekday: int | None = None,
    day_of_month: int | None = None,
    start_date: str | None = None,
    model: str | None = None,
    approval_mode: str = "manual",
    notes_enabled: bool = True,
    workflow: dict[str, Any] | None = None,
    environment: str | None = None,
    watch: dict[str, Any] | None = None,
    how: str = "created",
) -> ScheduledTrigger:
    """Validate and persist a new ScheduledTrigger. Shared by the model's create_scheduled_task
    and POST /api/scheduled-tasks (the UI's form), so the two can't drift apart."""
    rule, next_run_at, normalized_workflow = _validate_and_build_schedule(
        kind=kind,
        at=at,
        prompt=prompt,
        weekday=weekday,
        day_of_month=day_of_month,
        start_date=start_date,
        approval_mode=approval_mode,
        workflow=workflow,
        watch=watch,
    )

    trigger_id = uuid.uuid4().hex[:12]
    check_calls(store, trigger_id, normalized_workflow)
    trigger = ScheduledTrigger(
        trigger_id=trigger_id,
        name=name,
        schedule=rule,
        enabled=True,
        created_at=_now_iso(),
        next_run_at=next_run_at,
        prompt=prompt,
        model=model,
        approval_mode=approval_mode,
        notes_enabled=notes_enabled,
        workflow=normalized_workflow,
        environment=_checked_environment(store, environment),
    )
    _watch_folder(trigger)
    store.save(trigger)
    store.versions.keep(trigger_id, normalized_workflow, how)
    return trigger


def update_trigger(
    store: ScheduledTriggerStore,
    trigger_id: str,
    *,
    name: str,
    kind: str,
    at: str,
    prompt: str,
    weekday: int | None = None,
    day_of_month: int | None = None,
    start_date: str | None = None,
    model: str | None = None,
    approval_mode: str = "manual",
    notes_enabled: bool = True,
    workflow: dict[str, Any] | None = None,
    environment: str | None = None,
    watch: dict[str, Any] | None = None,
    how: str = "edited",
    restored_from: int | None = None,
) -> ScheduledTrigger:
    """Edit a trigger in place, validated as create_trigger does, so an edited task can't end up
    in a state a new one couldn't. Keeps its id, runs and pause; next_run_at is worked out again
    from now, as resuming a paused task does. A changed workflow is kept as a new version."""
    trigger = store.load(trigger_id)
    if trigger is None:
        raise KeyError(f"No scheduled task with id {trigger_id!r}")

    rule, next_run_at, normalized_workflow = _validate_and_build_schedule(
        kind=kind,
        at=at,
        prompt=prompt,
        weekday=weekday,
        day_of_month=day_of_month,
        start_date=start_date,
        approval_mode=approval_mode,
        workflow=workflow,
        watch=watch,
    )
    check_calls(store, trigger_id, normalized_workflow)
    before = trigger.workflow

    trigger.name = name
    trigger.schedule = rule
    trigger.next_run_at = next_run_at
    trigger.prompt = prompt
    trigger.model = model
    trigger.approval_mode = approval_mode
    trigger.notes_enabled = notes_enabled
    trigger.workflow = normalized_workflow
    trigger.environment = _checked_environment(store, environment)
    _watch_folder(trigger)
    store.save(trigger)
    store.versions.saved(trigger_id, before, normalized_workflow, how, restored_from)
    return trigger


def patch_trigger(
    store: ScheduledTriggerStore,
    trigger_id: str,
    changes: dict[str, Any],
    restored_from: int | None = None,
) -> ScheduledTrigger:
    """Change only the given fields, keeping the rest as stored -- not as a
    page last loaded them. Two cards saved one after the other (a workflow
    revision, then a settings edit) otherwise undo each other with stale
    copies of the fields they didn't mean to touch."""
    trigger = store.load(trigger_id)
    if trigger is None:
        raise KeyError(f"No scheduled task with id {trigger_id!r}")
    changes = dict(changes)
    draft = changes.pop("from_draft", None)
    auto_investigate = changes.pop("auto_investigate", None)
    rule = trigger.schedule
    current: dict[str, Any] = {
        "name": trigger.name,
        "kind": rule.kind,
        "at": rule.at,
        "prompt": trigger.prompt,
        "weekday": rule.weekday,
        "day_of_month": rule.day_of_month,
        "start_date": rule.start_date,
        "model": trigger.model,
        "approval_mode": trigger.approval_mode,
        "notes_enabled": trigger.notes_enabled,
        "workflow": trigger.workflow,
        "environment": trigger.environment,
        "watch": {k: getattr(rule, k) for k in _WATCH_FIELDS},
    }
    unknown = sorted(set(changes) - set(current))
    if unknown:
        raise ValueError(f"Can't change {', '.join(unknown)}")
    how = "restored" if restored_from is not None else "conversation" if draft else "edited"
    trigger = update_trigger(store, trigger_id, **{**current, **changes}, how=how,
                             restored_from=restored_from)  # fmt: skip
    if auto_investigate is not None:
        trigger.auto_investigate = bool(auto_investigate)
        store.save(trigger)
    if draft:
        record_draft(store, trigger, str(draft))
    return trigger


def record_draft(store: ScheduledTriggerStore, trigger: ScheduledTrigger, draft_id: str) -> None:
    """Note that the conversation draft `draft_id` was saved into `trigger`."""
    if draft_id not in trigger.drafts:
        trigger.drafts.append(draft_id)
        store.save(trigger)


def edit_draft(store: ScheduledTriggerStore, changes: dict[str, Any]) -> dict[str, Any]:
    """The whole task as edit_scheduled_task would leave it -- what the user
    reviews -- with `trigger_id` and the names of the fields it changes."""
    trigger = store.load(str(changes.get("trigger_id", "")))
    if trigger is None:
        raise KeyError(f"No scheduled task with id {changes.get('trigger_id')!r}")
    rule = trigger.schedule
    current: dict[str, Any] = {
        "name": trigger.name,
        "kind": "manual" if rule.kind == "once" else rule.kind,
        "at": rule.at,
        "prompt": trigger.prompt,
        "weekday": rule.weekday,
        "day_of_month": rule.day_of_month,
        "start_date": rule.start_date,
        "model": trigger.model,
        "approval_mode": trigger.approval_mode,
    }
    given = {k: v for k, v in changes.items() if k in _EDITABLE_FIELDS and v is not None}
    changed = [k for k, v in given.items() if v != current[k]]
    return {**current, **given, "trigger_id": trigger.trigger_id, "changed": changed}


def build_scheduled_task_tools(
    state_dir: str | Path, thread_id: str | None = None
) -> list[Callable[..., Any]]:
    """Return the Scheduled Tasks tool callables. They operate globally,
    not scoped to the calling thread -- a task is an independent entity,
    not tied to the conversation that created it. The one exception is
    update_task_notes, only present when `thread_id` is a run's own
    thread (see parse_run_thread_id), and only ever touching that run's
    own task.
    """
    store = ScheduledTriggerStore(state_dir)

    # Optional[X], not X | None: aisuite's Tools.__infer_from_signature
    # only unwraps typing.Optional (checks `get_origin(t) is Union`), and
    # PEP 604 `X | None` has origin `types.UnionType` instead -- it slips
    # through unwrapped and gets serialized as the literal string
    # "X | None" for the "type" field, which Gemini's strict
    # OpenAPI-subset schema rejects (see tools/office/xlsx/'s read_xlsx
    # for the same fix, applied first).
    def create_scheduled_task(
        name: str,
        kind: str,
        at: str,
        prompt: str,
        weekday: Optional[int] = None,  # noqa: UP045
        day_of_month: Optional[int] = None,  # noqa: UP045
        start_date: Optional[str] = None,  # noqa: UP045
        model: Optional[str] = None,  # noqa: UP045
        approval_mode: str = "manual",
    ) -> dict[str, Any]:
        """Draft a scheduled task (a reusable workflow) for the user to
        review -- they can edit any field before saving, or dismiss it;
        the result tells you which. Runs repeatedly on an hourly/daily/
        weekdays/weekly/monthly schedule, or only when the user starts it
        ("manual"), independent of whether any conversation is open. Each
        run starts in a brand-new conversation with none of this one's
        context, so `prompt` must stand on its own.

        Args:
            name: short, human-readable name, e.g. "Weekly sales report".
            kind: "manual", "hourly", "daily", "weekdays", "weekly", or
                "monthly".
            at: unused for kind="manual". For kind="hourly", "HH:MM" but
                only the minute is used (fires every hour at that
                minute). Otherwise a 24-hour "HH:MM" time of day, e.g.
                "09:00" -- interpreted in this machine's own local
                timezone.
            prompt: complete, standalone instructions for a run: the
                goal, the concrete steps and inputs that worked, pitfalls
                to avoid, and the expected output.
            weekday: required for kind="weekly" -- 0=Monday .. 6=Sunday.
            day_of_month: required for kind="monthly" -- 1-31 (clamped to
                the real last day of a shorter month).
            start_date: "YYYY-MM-DD" -- the schedule produces no
                occurrence before this date. Optional; defaults to
                starting immediately.
            model: "provider:model" to run this task with, e.g.
                "anthropic:claude-opus-5". Optional; defaults to the
                app's own configured default model.
            approval_mode: "manual" (pauses for every action needing
                approval -- the default), "auto" (creates and edits
                local files without asking, but pauses before running
                code or using connectors/downloads), or "skip" (never
                pauses, including for running code -- use with real
                caution for an unattended task).
        """
        trigger = create_trigger(
            store,
            name=name,
            kind=kind,
            at=at,
            prompt=prompt,
            weekday=weekday,
            day_of_month=day_of_month,
            start_date=start_date,
            model=model,
            approval_mode=approval_mode,
        )
        return trigger.to_dict()

    def edit_scheduled_task(
        trigger_id: str,
        name: Optional[str] = None,  # noqa: UP045
        kind: Optional[str] = None,  # noqa: UP045
        at: Optional[str] = None,  # noqa: UP045
        prompt: Optional[str] = None,  # noqa: UP045
        weekday: Optional[int] = None,  # noqa: UP045
        day_of_month: Optional[int] = None,  # noqa: UP045
        start_date: Optional[str] = None,  # noqa: UP045
        model: Optional[str] = None,  # noqa: UP045
        approval_mode: Optional[str] = None,  # noqa: UP045
    ) -> dict[str, Any]:
        """Propose changes to a saved scheduled task -- its instructions,
        name, schedule, model or approval setting. The user reviews the
        changed task and saves or dismisses it; the result tells you which.
        Its runs, notes and (for a workflow task) steps are kept; to change a
        workflow's steps, use revise_workflow. Pass only what changes, as
        create_scheduled_task describes each field.

        Args:
            trigger_id: the task's id, from list_scheduled_tasks.
            name: new name.
            kind: new frequency: "manual", "hourly", "daily", "weekdays",
                "weekly" or "monthly".
            at: new "HH:MM" time.
            prompt: the complete new instructions (not a diff).
            weekday: for weekly, 0=Monday .. 6=Sunday.
            day_of_month: for monthly, 1-31.
            start_date: "YYYY-MM-DD".
            model: "provider:model".
            approval_mode: "manual", "auto" or "skip".
        """
        draft = edit_draft(
            store,
            {
                "trigger_id": trigger_id,
                "name": name,
                "kind": kind,
                "at": at,
                "prompt": prompt,
                "weekday": weekday,
                "day_of_month": day_of_month,
                "start_date": start_date,
                "model": model,
                "approval_mode": approval_mode,
            },
        )
        trigger = _load_or_raise(trigger_id)
        updated = update_trigger(
            store,
            trigger_id,
            name=draft["name"],
            kind=draft["kind"],
            at=draft["at"],
            prompt=draft["prompt"],
            weekday=draft["weekday"],
            day_of_month=draft["day_of_month"],
            start_date=draft["start_date"],
            model=draft["model"],
            approval_mode=draft["approval_mode"],
            notes_enabled=trigger.notes_enabled,
            workflow=trigger.workflow,
            environment=trigger.environment,
        )
        return updated.to_dict()

    def list_scheduled_tasks() -> list[dict[str, Any]]:
        """List every scheduled task, across all conversations."""
        return [t.to_dict() for t in store.list_all()]

    def _load_or_raise(trigger_id: str) -> ScheduledTrigger:
        trigger = store.load(trigger_id)
        if trigger is None:
            raise KeyError(f"No scheduled task with id {trigger_id!r}")
        return trigger

    def pause_scheduled_task(trigger_id: str) -> dict[str, Any]:
        """Pause a scheduled task -- it won't fire again until resumed.

        Args:
            trigger_id: id of the task, as returned by create_scheduled_task
                or list_scheduled_tasks.
        """
        trigger = _load_or_raise(trigger_id)
        trigger.enabled = False
        store.save(trigger)
        return trigger.to_dict()

    def resume_scheduled_task(trigger_id: str) -> dict[str, Any]:
        """Resume a paused scheduled task. Its next run time is recomputed
        from now (a task paused for two weeks won't fire twenty times
        back to back on resume).

        Args:
            trigger_id: id of the task, as returned by create_scheduled_task
                or list_scheduled_tasks.
        """
        trigger = _load_or_raise(trigger_id)
        trigger.enabled = True
        trigger.next_run_at = compute_next_run_at(trigger.schedule, datetime.now())
        store.save(trigger)
        return trigger.to_dict()

    def delete_scheduled_task(trigger_id: str) -> dict[str, Any]:
        """Permanently delete a scheduled task.

        Args:
            trigger_id: id of the task, as returned by create_scheduled_task
                or list_scheduled_tasks.
        """
        if not store.delete(trigger_id):
            raise KeyError(f"No scheduled task with id {trigger_id!r}")
        return {"deleted": trigger_id}

    category = "scheduled_tasks"
    run = parse_run_thread_id(thread_id) if thread_id else None
    extra: list[Callable[..., Any]] = []
    if run is not None:
        own_trigger_id = run[0]

        def update_task_notes(notes: str) -> dict[str, Any]:
            """Replace this scheduled task's notes -- your memory across its
            runs, shown to you at the start of every future run. Write the
            full updated notes (not a diff): progress markers, where you
            left off, what changed, pitfalls worth remembering. Drop
            anything stale. Keep them short.

            Args:
                notes: the complete new notes, plain text or markdown.
            """
            store.write_notes(own_trigger_id, notes.strip())
            return {"saved": True, "characters": len(notes.strip())}

        # READ tier: the notes are the task's own bookkeeping, not user
        # content -- gating them would park every "ask first" run on an
        # approval nobody is there to give.
        extra.append(tool_metadata(update_task_notes, risk_category="READ", category=category))
    return extra + [
        tool_metadata(create_scheduled_task, risk_category="WRITE_LOCAL", category=category),
        tool_metadata(edit_scheduled_task, risk_category="WRITE_LOCAL", category=category),
        tool_metadata(list_scheduled_tasks, risk_category="READ", category=category),
        tool_metadata(pause_scheduled_task, risk_category="WRITE_LOCAL", category=category),
        tool_metadata(resume_scheduled_task, risk_category="WRITE_LOCAL", category=category),
        tool_metadata(delete_scheduled_task, risk_category="WRITE_LOCAL", category=category),
    ]
