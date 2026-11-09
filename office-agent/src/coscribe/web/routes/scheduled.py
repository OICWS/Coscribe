"""Scheduled routes."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, cast

from fastapi import (
    APIRouter,
    Body,
)
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ...config import side_model_name
from ...coordinator import build_coordinator_agent
from ...runtime import get_tool_metadata, load_custom_providers
from ...runtime_lg import (
    continue_workflow_run,
    resolve_chat_model,
    start_investigation,
    stop_run,
)
from ...tools import (
    ScheduledTriggerStore,
    compute_next_run_at,
    create_trigger,
    patch_trigger,
    record_draft,
    update_trigger,
)
from ...workflow_spec import ParallelStep, Workflow, task_results
from ...workflows import (
    BranchStep,
    ChoiceStep,
    LoopStep,
    added_fix,
    answer_problem,
    brings_outside_content,
    called_permissions,
    compiled_graph,
    heal_fixes,
    heals_to_revise,
    parse_workflow,
    run_report,
    summarize,
    walk,
    workflow_error,
    write_overview,
)
from ..schemas import (
    InvestigateRequest,
    PermissionsRequest,
    RunNowRequest,
    ScheduledTaskCreate,
    TaskMemoryUpdate,
    TaskNotesUpdate,
    WorkflowAnswer,
    WorkflowCheck,
    WorkflowRetry,
)
from ..state import AppState


class _NoSocket:
    """Stands in for a websocket where nobody is listening."""

    async def send_json(self, data: dict[str, Any]) -> None:
        return None


def _waiting_permission(run: Any) -> dict[str, Any] | None:
    """What the run's waiting step asks to be allowed, if it is asking, and which step asks."""
    for record in reversed(run.steps):
        if record.get("status") == "waiting":
            asked = record.get("permission")
            return {**asked, "step_id": record["step_id"]} if isinstance(asked, dict) else None
    return None


def _results(workflow: dict[str, Any] | None) -> list[str]:
    """What a run of a workflow task gives a task that runs it (decision 0035)."""
    try:
        return list(task_results(parse_workflow(workflow))) if workflow else []
    except ValidationError:
        return []


def _owner(trigger: Any, run: Any, step_id: str) -> tuple[str, Any]:
    """The task a step of this run belongs to, and its workflow: a called task's step
    (decision 0035) is `<step>/<its step>`, under the definition the run recorded."""
    path = step_id.rpartition("/")[0]
    if not path:
        return trigger.trigger_id, trigger.workflow
    called = run.called.get(path) or {}
    return str(called.get("task") or trigger.trigger_id), called.get("workflow")


def _answer_problem(trigger: Any, run: Any, payload: WorkflowAnswer) -> str | None:
    """Why the values sent to a waiting ask step won't do, so the person can fix them before
    the run goes on (decision 0033); None when they will, or nothing asks for values."""
    if trigger is None or run is None or not trigger.workflow or payload.values is None:
        return None
    waiting = next((r for r in reversed(run.steps) if r.get("status") == "waiting"), None)
    if waiting is None:
        return None
    _task, workflow = _owner(trigger, run, waiting["step_id"])
    if not workflow:
        return None
    steps = {p.step.id: p.step for p in walk(parse_workflow(workflow).steps)}
    step = steps.get(waiting["step_id"].rpartition("/")[2])
    return answer_problem(step, payload.values) if step is not None else None


def _workflow_routes(router: APIRouter, state: AppState) -> None:
    settings = state.settings
    _session_extra_tools = state.session_extra_tools

    @router.post("/api/workflows/validate")
    async def validate_workflow(body: WorkflowCheck) -> JSONResponse:
        try:
            workflow = parse_workflow(body.workflow)
        except ValidationError as exc:
            return JSONResponse({"error": workflow_error(exc, body.workflow)}, status_code=400)
        return JSONResponse({"workflow": workflow.model_dump(mode="json")})

    async def workflow_graph(body: WorkflowCheck) -> JSONResponse:
        try:
            workflow = parse_workflow(body.workflow)
        except ValidationError as exc:
            return JSONResponse({"error": workflow_error(exc, body.workflow)}, status_code=400)
        return JSONResponse(compiled_graph(workflow))

    router.add_api_route("/api/workflows/graph", workflow_graph, methods=["POST"])

    def _tool_facts() -> tuple[dict[str, str], set[str]]:
        """Each tool's risk tier, and the tools that bring in outside
        content: the browser, the web tools and every connector."""
        risks: dict[str, str] = {}
        outside: set[str] = set()
        for connector_tool in _session_extra_tools():
            metadata = get_tool_metadata(connector_tool)
            if (metadata.category or "").startswith("mcp:"):
                risks[connector_tool.name] = metadata.risk_category
            if brings_outside_content(metadata.category):
                outside.add(connector_tool.name)
        for tool in build_coordinator_agent(settings, thread_id="__tools_probe__").tools:
            metadata = get_tool_metadata(tool)
            risks[tool.__name__] = metadata.risk_category
            if brings_outside_content(metadata.category):
                outside.add(tool.__name__)
        return risks, outside

    @router.post("/api/workflows/permissions")
    async def workflow_permissions(body: PermissionsRequest) -> JSONResponse:
        """What a workflow will touch -- shown where it's reviewed -- and,
        given an earlier version, what this one adds to it."""
        try:
            workflow = parse_workflow(body.workflow)
            earlier = parse_workflow(body.previous) if body.previous is not None else None
        except ValidationError as exc:
            return JSONResponse({"error": workflow_error(exc, body.workflow)}, status_code=400)
        trigger = (
            ScheduledTriggerStore(settings.state_dir).load(body.trigger_id)
            if body.trigger_id
            else None
        )
        granted = trigger.permissions if trigger is not None else None
        if earlier is None and body.against_saved and trigger is not None and trigger.workflow:
            earlier = parse_workflow(trigger.workflow)
        risks, outside = _tool_facts()
        store = ScheduledTriggerStore(settings.state_dir)
        summary = summarize(workflow, risks, granted, outside)
        # What each task it runs may use is that task's own (decision 0035).
        summary["tasks"] = called_permissions(store.calls.tasks(body.workflow))
        added: dict[str, Any] | None = None
        if earlier is not None:
            before = summarize(earlier, risks, granted, outside)
            earlier_json = earlier.model_dump(mode="json")
            ran_before = {t.trigger_id for t in store.calls.tasks(earlier_json)}
            added = {
                "folders": [f for f in summary["folders"] if f not in before["folders"]],
                "sites": [x for x in summary["sites"] if x not in before["sites"]],
                "scripts": [t for t in summary["scripts"] if t not in before["scripts"]],
                "notable": [
                    n
                    for n in summary["notable"]
                    if n["tool"] not in {b["tool"] for b in before["notable"]}
                ],
                "agents": [a for a in summary["agents"] if a not in before["agents"]],
                "tasks": [t for t in summary["tasks"] if t["task"] not in ran_before],
            }
        return JSONResponse({"permissions": summary, "added": added})


def _items_checked(store: ScheduledTriggerStore, trigger: Any) -> dict[str, Any]:
    """A connector task's latest check and the items that started no run (decision 0039); a
    webhook task's latest event and the events that started none (decision 0040)."""
    if trigger.schedule.kind == "connector":
        return {"connector_check": store.connector_items.shown(trigger.trigger_id)}
    if trigger.schedule.kind == "webhook":
        return {"webhook": store.webhooks.shown(trigger.trigger_id)}
    return {}


def _task_routes(router: APIRouter, state: AppState) -> None:
    settings = state.settings

    # -- /api/scheduled-tasks -- the Settings > Scheduled Tasks panel's
    # create-without-a-conversation entry point; direct ScheduledTriggerStore
    # reads/writes, no session/graph involved. POST reuses create_trigger
    # (tools/bookkeeping/scheduled_tasks.py) -- the exact same validation
    # create_scheduled_task (the model tool) uses, so the two creation
    # paths can't silently drift apart.

    @router.get("/api/scheduled-tasks")
    async def list_scheduled_tasks_endpoint() -> list[dict[str, Any]]:
        store = ScheduledTriggerStore(settings.state_dir)
        # A task saved before versions were kept is shown as its version 1 (decision 0035).
        return [{**t.to_dict(), "version": store.versions.current(t.trigger_id) or 1,
                 "results": _results(t.workflow), **_items_checked(store, t)}
                for t in store.list_all()]  # fmt: skip

    @router.post("/api/scheduled-tasks")
    async def create_scheduled_task_endpoint(payload: ScheduledTaskCreate) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        try:
            trigger = create_trigger(
                store,
                name=payload.name,
                kind=payload.kind,
                at=payload.at,
                prompt=payload.prompt,
                weekday=payload.weekday,
                day_of_month=payload.day_of_month,
                start_date=payload.start_date,
                model=payload.model,
                approval_mode=payload.approval_mode,
                notes_enabled=payload.notes_enabled,
                workflow=payload.workflow,
                environment=payload.environment,
                watch=payload.watch,
                how="conversation" if payload.from_draft else "created",
            )
        except (ValueError, KeyError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        if payload.from_thread:
            trigger.source_thread = payload.from_thread
            store.save(trigger)
        if payload.from_draft:
            record_draft(store, trigger, payload.from_draft)
        await state.webhooks.sync()
        return JSONResponse(trigger.to_dict())

    @router.put("/api/scheduled-tasks/{trigger_id}")
    async def update_scheduled_task_endpoint(
        trigger_id: str, payload: ScheduledTaskCreate
    ) -> JSONResponse:
        try:
            trigger = update_trigger(
                ScheduledTriggerStore(settings.state_dir),
                trigger_id,
                name=payload.name,
                kind=payload.kind,
                at=payload.at,
                prompt=payload.prompt,
                weekday=payload.weekday,
                day_of_month=payload.day_of_month,
                start_date=payload.start_date,
                model=payload.model,
                approval_mode=payload.approval_mode,
                notes_enabled=payload.notes_enabled,
                workflow=payload.workflow,
                environment=payload.environment,
                watch=payload.watch,
            )
        except KeyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        await state.webhooks.sync()
        return JSONResponse(trigger.to_dict())

    @router.patch("/api/scheduled-tasks/{trigger_id}")
    async def patch_scheduled_task_endpoint(
        trigger_id: str, changes: Annotated[dict[str, Any], Body()]
    ) -> JSONResponse:
        try:
            trigger = patch_trigger(ScheduledTriggerStore(settings.state_dir), trigger_id, changes)
        except KeyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        await state.webhooks.sync()
        return JSONResponse(trigger.to_dict())


def _run_control_routes(router: APIRouter, state: AppState) -> None:
    settings = state.settings
    _get_session_async = state.get_session_async
    _delete_run_threads = state.delete_run_threads
    _execute_and_announce = state.execute_and_announce
    _track_background = state.track_background

    @router.post("/api/scheduled-tasks/{trigger_id}/run")
    async def run_scheduled_task_now_endpoint(
        trigger_id: str, payload: RunNowRequest | None = None
    ) -> JSONResponse:
        # Returns as soon as the run is recorded, not when it finishes: the
        # browser opens the run's own conversation right away and watches
        # it stream there (see runtime_lg/scheduled_tasks.py's
        # _RelaySocket). How it ended lands on the run record.
        store = ScheduledTriggerStore(settings.state_dir)
        try:
            trigger, run, pruned = store.start_run(
                trigger_id, "manual", payload.inputs if payload else None
            )
        except KeyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        await _delete_run_threads(pruned)
        _track_background(asyncio.create_task(_execute_and_announce(trigger_id, run.run_id)))
        return JSONResponse({"task": trigger.to_dict(), "run": run.to_dict()})

    @router.post("/api/scheduled-tasks/{trigger_id}/runs/{run_id}/stop")
    async def stop_workflow_run(trigger_id: str, run_id: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        run = trigger.find_run(run_id) if trigger is not None else None
        if trigger is None or run is None:
            return JSONResponse({"error": f"No run {run_id!r}"}, status_code=404)
        if run.status == "waiting":
            # Paused at a wait step, it holds nothing to cancel (decision 0033).
            store.finish_run(trigger_id, run_id, "stopped")
            return JSONResponse({"ok": True})
        if run.status != "running" or not stop_run(run_id, run.thread_id):
            return JSONResponse({"error": "This run isn't going"}, status_code=409)
        return JSONResponse({"ok": True})

    @router.get("/api/scheduled-tasks/{trigger_id}/runs/{run_id}/report")
    async def workflow_run_report(trigger_id: str, run_id: str) -> JSONResponse:
        trigger = ScheduledTriggerStore(settings.state_dir).load(trigger_id)
        run = trigger.find_run(run_id) if trigger is not None else None
        if trigger is None or trigger.workflow is None or run is None:
            return JSONResponse({"error": f"No workflow run {run_id!r}"}, status_code=404)
        workflow = parse_workflow(trigger.workflow)
        report = run_report(workflow, run.steps, run.started_at, run.finished_at, run.called)
        report["versions"] = run.versions
        fixes = heal_fixes(trigger.workflow, report["healed"])
        added = added_fix(trigger.workflow, report["added"])
        return JSONResponse({**report, "fixes": fixes, "added_fix": added})

    @router.post("/api/scheduled-tasks/{trigger_id}/runs/{run_id}/investigate")
    async def investigate_workflow_run(
        trigger_id: str, run_id: str, payload: InvestigateRequest | None = None
    ) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        run = trigger.find_run(run_id) if trigger is not None else None
        if trigger is None or trigger.workflow is None or run is None:
            return JSONResponse({"error": f"No workflow run {run_id!r}"}, status_code=404)
        if run.status != "failed" and not heals_to_revise(trigger.workflow, run.status, run.steps):
            message = "Only a failed run, or one with heals to revise, can be looked into"
            return JSONResponse({"error": message}, status_code=409)
        thread_id = uuid.uuid4().hex[:8]
        _track_background(
            asyncio.create_task(
                start_investigation(
                    settings.state_dir,
                    trigger_id,
                    run_id,
                    thread_id,
                    payload.model if payload else None,
                    _get_session_async,
                    attended=True,
                )
            )
        )
        return JSONResponse({"thread_id": thread_id})


def _run_reopeners(state: AppState) -> tuple[Callable[..., Any], Callable[..., None]]:
    settings = state.settings
    _get_session_async = state.get_session_async
    _track_background = state.track_background
    _announce_run = state.announce_run

    def _reopen_workflow_run(trigger_id: str, run_id: str) -> tuple[Any, Any] | JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None or trigger.workflow is None:
            return JSONResponse({"error": f"No workflow task {trigger_id!r}"}, status_code=404)
        existing = trigger.find_run(run_id)
        if existing is None:
            return JSONResponse({"error": f"No run {run_id!r}"}, status_code=404)
        try:
            run = store.reopen_run(trigger_id, run_id)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=409)
        return existing, run

    def _continue_in_background(trigger_id: str, run_id: str, action: Any) -> None:
        async def go() -> None:
            run = await continue_workflow_run(
                settings.state_dir, trigger_id, run_id, _get_session_async, action
            )
            await _announce_run(trigger_id, run)

        _track_background(asyncio.create_task(go()))

    return _reopen_workflow_run, _continue_in_background


def _approval_routes(router: APIRouter, state: AppState) -> None:
    settings = state.settings
    _get_session_async = state.get_session_async
    _write_workspace_sidecar = state.thread_files.write_workspace_sidecar
    _reopen_workflow_run, _continue_in_background = _run_reopeners(state)

    async def _allow_for_run(
        store: ScheduledTriggerStore, trigger_id: str, thread_id: str, permission: dict[str, Any]
    ) -> str | None:
        """Record the answer on the task, so later runs don't ask again, and
        open the folder to the run's session. A problem, or None."""
        target = str(permission.get("target") or "")
        if permission.get("kind") == "folder":
            session = await _get_session_async(thread_id)
            if not await session.add_folder(target, cast(Any, _NoSocket())):
                return f"Couldn't add {target} -- is it still there?"
            _write_workspace_sidecar(thread_id, [str(f) for f in session.folders])
            store.grant(trigger_id, "folders", target)
        elif permission.get("kind") == "site":
            store.grant(trigger_id, "sites", target)
        return None

    @router.post("/api/scheduled-tasks/{trigger_id}/runs/{run_id}/answer")
    async def answer_workflow_approval(
        trigger_id: str, run_id: str, payload: WorkflowAnswer
    ) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        before = trigger.find_run(run_id) if trigger is not None else None
        if before is not None and before.status not in ("needs_approval", "waiting"):
            return JSONResponse({"error": "This run isn't waiting for approval"}, status_code=409)
        problem = _answer_problem(trigger, before, payload) if payload.approved else None
        if problem:
            return JSONResponse({"error": problem}, status_code=422)
        permission = _waiting_permission(before) if before is not None else None
        if payload.approved and permission is not None and before is not None:
            # Granted to the task whose step asked, a called one's own (decision 0035).
            asking = permission.get("step_id") or ""
            owner = _owner(trigger, before, asking)[0] if trigger is not None else trigger_id
            problem = await _allow_for_run(store, owner, before.thread_id, permission)
            if problem:
                return JSONResponse({"error": problem}, status_code=409)
        reopened = _reopen_workflow_run(trigger_id, run_id)
        if isinstance(reopened, JSONResponse):
            return reopened
        _continue_in_background(
            trigger_id, run_id, lambda wf: wf.answer(payload.approved, payload.note, payload.values)
        )
        return JSONResponse({"run": reopened[1].to_dict()})


def _retry_routes(router: APIRouter, state: AppState) -> None:
    settings = state.settings
    _reopen_workflow_run, _continue_in_background = _run_reopeners(state)

    @router.post("/api/scheduled-tasks/{trigger_id}/runs/{run_id}/retry")
    async def retry_workflow_run(
        trigger_id: str, run_id: str, payload: WorkflowRetry
    ) -> JSONResponse:
        reopened = _reopen_workflow_run(trigger_id, run_id)
        if isinstance(reopened, JSONResponse):
            return reopened
        before, run = reopened
        trigger = ScheduledTriggerStore(settings.state_dir).load(trigger_id)
        workflow = parse_workflow(trigger.workflow) if trigger and trigger.workflow else None
        # A loop or branch around the failed step is recorded as failed
        # too; retrying means the step itself, on the pass that failed.
        blocks = (
            {
                p.step.id
                for p in walk(workflow.steps)
                if isinstance(p.step, (BranchStep, ChoiceStep, LoopStep))
            }
            if workflow
            else set()
        )
        step_id = payload.step_id or next(
            (
                s["step_id"]
                for s in reversed(before.steps)
                if s.get("status") == "failed" and s["step_id"] not in blocks
            ),
            None,
        )
        # A called task's step goes on inside the step that runs it (decision 0035), a lane's
        # inside its parallel step (decision 0036).
        if step_id is None or "/" in step_id or (workflow and step_id in _lane_steps(workflow)):
            _continue_in_background(trigger_id, run_id, lambda wf: wf.resume())
        else:
            _continue_in_background(trigger_id, run_id, lambda wf: wf.retry_from(step_id))
        return JSONResponse({"run": run.to_dict()})


def _lane_steps(workflow: Workflow) -> set[str]:
    """The steps inside a parallel step's lanes, each run of its own (decision 0036)."""
    lanes = [p.step.lanes for p in walk(workflow.steps) if isinstance(p.step, ParallelStep)]
    return {q.step.id for each in lanes for lane in each for q in walk(lane.steps)}


def _note_and_lifecycle_routes(router: APIRouter, state: AppState) -> None:
    settings = state.settings
    _delete_run_threads = state.delete_run_threads

    @router.get("/api/scheduled-tasks/{trigger_id}/notes")
    async def get_scheduled_task_notes(trigger_id: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        if store.load(trigger_id) is None:
            return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)
        return JSONResponse({"notes": store.read_notes(trigger_id)})

    @router.put("/api/scheduled-tasks/{trigger_id}/notes")
    async def put_scheduled_task_notes(trigger_id: str, payload: TaskNotesUpdate) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        if store.load(trigger_id) is None:
            return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)
        try:
            store.write_notes(trigger_id, payload.notes.strip())
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"notes": store.read_notes(trigger_id)})

    @router.post("/api/scheduled-tasks/{trigger_id}/pause")
    async def pause_scheduled_task_endpoint(trigger_id: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None:
            return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)
        trigger.enabled = False
        store.save(trigger)
        await state.webhooks.sync()
        return JSONResponse(trigger.to_dict())

    @router.post("/api/scheduled-tasks/{trigger_id}/resume")
    async def resume_scheduled_task_endpoint(trigger_id: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None:
            return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)
        trigger.enabled = True
        trigger.next_run_at = compute_next_run_at(trigger.schedule, datetime.now())
        store.save(trigger)
        await state.webhooks.sync()
        return JSONResponse(trigger.to_dict())

    @router.delete("/api/scheduled-tasks/{trigger_id}")
    async def delete_scheduled_task_endpoint(trigger_id: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None or not store.delete(trigger_id):
            return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)
        await _delete_run_threads(trigger.runs)
        await state.webhooks.sync()
        return JSONResponse({"deleted": trigger_id})


def _memory_routes(router: APIRouter, state: AppState) -> None:
    """What a task remembers between runs (decision 0034), which a person may correct."""
    settings = state.settings

    async def get_task_memory(trigger_id: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        if store.load(trigger_id) is None:
            return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)
        return JSONResponse({"memory": store.memory.entries(trigger_id)})

    async def put_task_memory(
        trigger_id: str, name: str, payload: TaskMemoryUpdate
    ) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None or trigger.workflow is None:
            return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)
        declared = parse_workflow(trigger.workflow).memory
        entry = next((m for m in declared if m.name == name), None)
        if entry is None:
            return JSONResponse({"error": f"This task doesn't remember {name!r}"}, status_code=404)
        try:
            store.memory.set(trigger_id, declared, name, payload.value)
        except ValueError:
            # Said from the entry, not the exception, so no internal text reaches the page.
            kind = {"list": "a list", "date": "a date like 2026-03-31", "number": "a number"}
            keeps = kind.get(entry.type, "text")
            problem = f"“{entry.label or name}” keeps {keeps}, and not too long"
            return JSONResponse({"error": problem}, status_code=400)
        return JSONResponse({"memory": store.memory.entries(trigger_id)})

    path = "/api/scheduled-tasks/{trigger_id}/memory"
    router.add_api_route(path, get_task_memory, methods=["GET"])
    router.add_api_route(path + "/{name}", put_task_memory, methods=["PUT"])


def _version_routes(router: APIRouter, state: AppState) -> None:
    """Every workflow a task was saved with, and putting one back (decision 0035)."""
    settings = state.settings

    async def task_versions(trigger_id: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None or trigger.workflow is None:
            return JSONResponse({"error": f"No workflow task {trigger_id!r}"}, status_code=404)
        versions = store.versions.all(trigger_id)
        if not versions:
            # Saved before versions were kept: what it holds is its first, not yet written.
            versions = [{"number": 1, "how": "found", "saved_at": trigger.created_at,
                         "workflow": trigger.workflow}]  # fmt: skip
        return JSONResponse({"current": versions[-1]["number"], "versions": versions[::-1]})

    async def restore_task_version(trigger_id: str, number: int) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        version = store.versions.get(trigger_id, number)
        if store.load(trigger_id) is None or version is None:
            return JSONResponse({"error": f"There is no version {number}"}, status_code=404)
        problem = store.calls.problem(trigger_id, version["workflow"])
        if problem:
            return JSONResponse({"error": f"Version {number} can't come back: {problem}"},
                                status_code=409)  # fmt: skip
        try:
            trigger = patch_trigger(store, trigger_id, {"workflow": version["workflow"]},
                                    restored_from=number)  # fmt: skip
        except (KeyError, ValueError):
            message = f"Version {number} no longer fits what a task can be; copy what you need"
            return JSONResponse({"error": message}, status_code=409)
        return JSONResponse({**trigger.to_dict(), "version": store.versions.current(trigger_id)})

    path = "/api/scheduled-tasks/{trigger_id}/versions"
    router.add_api_route(path, task_versions, methods=["GET"])
    router.add_api_route(path + "/{number}/restore", restore_task_version, methods=["POST"])


def _overview_model(settings: Any) -> Any:
    """The side model (`Settings.side_model`), falling back to the default one, as a title is."""
    path = settings.providers_config_path
    custom = load_custom_providers(path) if path is not None else {}
    main = resolve_chat_model(settings.default_model, custom)
    name = side_model_name(settings.default_model, settings.side_model)
    if name == settings.default_model:
        return main
    try:
        return resolve_chat_model(name, custom).with_fallbacks([main])
    except (ValueError, ImportError):
        return main


def _overview_routes(router: APIRouter, state: AppState) -> None:
    """The sentence the simple view opens a task with. A model writes it once per saved version;
    one the person wrote is kept whatever the version."""
    settings = state.settings
    writing: dict[str, asyncio.Lock] = {}

    async def overview(trigger_id: str) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None or trigger.workflow is None:
            return JSONResponse({"error": f"No workflow task {trigger_id!r}"}, status_code=404)
        # Two pages opening the task at once make one call, not two.
        async with writing.setdefault(trigger_id, asyncio.Lock()):
            version = store.versions.current(trigger_id) or 1
            kept = store.versions.overview(trigger_id)
            if kept and (kept.get("by") == "you" or kept.get("version") == version):
                return JSONResponse(kept)
            try:
                text = await write_overview(_overview_model(settings), trigger.name,
                                            parse_workflow(trigger.workflow))  # fmt: skip
            # Any failure of the call (no key, no network, a refusal) leaves the page without one.
            except Exception:
                return JSONResponse({"text": None})
            if not text:
                return JSONResponse({"text": None})
            store.versions.set_overview(trigger_id, text, version, "ai")
            return JSONResponse({"text": text, "version": version, "by": "ai"})

    async def put_overview(trigger_id: str, text: Annotated[str, Body(embed=True)]) -> JSONResponse:
        store = ScheduledTriggerStore(settings.state_dir)
        if store.load(trigger_id) is None:
            return JSONResponse({"error": f"No scheduled task {trigger_id!r}"}, status_code=404)
        line = " ".join(text.split())[:300]
        if not line:
            # Cleared: the next look writes one again.
            store.versions.clear_overview(trigger_id)
            return JSONResponse({"text": None})
        version = store.versions.current(trigger_id) or 1
        store.versions.set_overview(trigger_id, line, version, "you")
        return JSONResponse({"text": line, "version": version, "by": "you"})

    path = "/api/scheduled-tasks/{trigger_id}/overview"
    # A POST, though it mostly reads: a first look at a version spends a model call.
    router.add_api_route(path, overview, methods=["POST"])
    router.add_api_route(path, put_overview, methods=["PUT"])


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    _workflow_routes(router, state)
    _task_routes(router, state)
    _run_control_routes(router, state)
    _approval_routes(router, state)
    _retry_routes(router, state)
    _note_and_lifecycle_routes(router, state)
    _memory_routes(router, state)
    _version_routes(router, state)
    _overview_routes(router, state)
    return router
