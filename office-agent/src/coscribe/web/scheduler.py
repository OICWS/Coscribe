"""The loop that fires due wakes and scheduled tasks while the web process runs, announces
how each run ended, and removes the conversations of runs no task lists any more. Reads
settings and the state dir, nothing from FastAPI, so it runs without building the app."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable, Coroutine, Mapping
from typing import Any, Protocol

from ..config import Settings
from ..runtime_lg import execute_run, start_investigation
from ..tools import (
    SCHEDULED_THREAD_PREFIX,
    ScheduledRun,
    ScheduledTriggerStore,
)
from .background_events import BackgroundEvent, BackgroundEventBus, run_event


class _LiveSession(Protocol):
    async def notify_resync(self) -> None: ...


class Scheduler:
    def __init__(
        self,
        settings: Settings,
        sessions: Mapping[str, _LiveSession],
        background_events: BackgroundEventBus,
        get_session_async: Callable[[str], Coroutine[Any, Any, Any]],
        delete_thread_data: Callable[[str], Coroutine[Any, Any, bool]],
        checkpointer: Callable[[], Any],
        poll_due_wakes: Callable[..., Coroutine[Any, Any, Any]],
        poll_due_scheduled_tasks: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        self._settings = settings
        self._sessions = sessions
        self._background_events = background_events
        self._get_session_async = get_session_async
        self._delete_thread_data = delete_thread_data
        self._checkpointer = checkpointer
        self._poll_due_wakes = poll_due_wakes
        self._poll_due_scheduled_tasks = poll_due_scheduled_tasks
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._wake_poll_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._wake_poll_task = asyncio.create_task(self.wake_poll_loop())

    async def stop(self) -> None:
        if self._wake_poll_task is not None:
            self._wake_poll_task.cancel()
            try:
                await self._wake_poll_task
            except asyncio.CancelledError:
                pass
        for task in list(self._background_tasks):
            task.cancel()
        await asyncio.gather(*self._background_tasks, return_exceptions=True)

    async def wake_poll_loop(self) -> None:
        """Runs for the life of the web process, checking for due
        sleep_until/sleep_for/wake_on/wake_on_event requests *and* due
        Scheduled Tasks every settings.wake_poll_seconds -- the
        zero-config half of both Phase 4's suspend/resume story and the
        Scheduled Tasks feature built on top of it (cli.py's --check-wakes
        flag is the other half, for a setup that doesn't keep the web
        server running). One poll checking two stores, not two separate
        background tasks -- they share the same "periodically check for
        due things" shape. One bad poll iteration (of either kind) is
        logged and skipped, not fatal to the loop -- same defensive
        posture poll_due_wakes/poll_due_scheduled_tasks themselves take
        per item."""
        while True:
            await asyncio.sleep(self._settings.wake_poll_seconds)
            try:
                fired_wakes = await self._poll_due_wakes(
                    self._settings.state_dir, self._get_session_async
                )
                for wake in fired_wakes:
                    self._background_events.publish(
                        BackgroundEvent(
                            kind="wake",
                            status="completed",
                            title=wake.reason,
                            thread_id=wake.thread_id,
                        )
                    )
                    # poll_due_wakes already resumed wake.thread_id's own
                    # checkpointer correctly (via SilentSocket) -- this
                    # is the other half, nudging a *live* browser tab (if
                    # any) that was already open on that thread to go
                    # re-fetch it, closing the real, previously-documented
                    # gap where a poller-triggered resume wrote correctly
                    # but never appeared in an already-open tab until its
                    # next reload/reconnect. A no-op if no tab is open on
                    # that thread right now (see notify_resync's own
                    # docstring).
                    live_session = self._sessions.get(wake.thread_id)
                    if live_session is not None:
                        await live_session.notify_resync()
            except Exception:
                logging.getLogger(__name__).exception("selfwake: poll_due_wakes failed")
            # Backgrounded rather than awaited: a run can take minutes, and
            # due wakes must keep being checked meanwhile. Overlapping polls
            # can't double-fire a task -- its schedule advances before the
            # run's first await (see poll_due_scheduled_tasks).
            self.track_background(asyncio.create_task(self.poll_scheduled_tasks_once()))

    async def poll_scheduled_tasks_once(self) -> None:
        try:
            fired_triggers = await self._poll_due_scheduled_tasks(
                self._settings.state_dir, self._get_session_async, on_pruned=self.delete_run_threads
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "scheduled_tasks: poll_due_scheduled_tasks failed"
            )
            return
        for trigger in fired_triggers:
            if trigger.runs:
                await self.announce_run(trigger.trigger_id, trigger.runs[-1])

    async def announce_run(self, trigger_id: str, run: ScheduledRun | None) -> None:
        """Tell the desktop app how a run ended -- and, for a failed run of a
        task set to, start a conversation looking into it first, so the
        notification can open that."""
        if run is None:
            return
        store = ScheduledTriggerStore(self._settings.state_dir)
        trigger = store.load(trigger_id)
        if trigger is None:
            return
        investigation = None
        if (
            run.status == "failed"
            and trigger.auto_investigate
            and trigger.workflow is not None
            and run.investigation is None
        ):
            investigation = uuid.uuid4().hex[:8]
            self.track_background(
                asyncio.create_task(
                    start_investigation(
                        self._settings.state_dir,
                        trigger_id,
                        run.run_id,
                        investigation,
                        None,
                        self._get_session_async,
                        attended=False,
                    )
                )
            )
        event = run_event(trigger, run, investigation)
        if event is not None:
            self._background_events.publish(event)

    async def execute_and_announce(self, trigger_id: str, run_id: str) -> None:
        run = await execute_run(
            self._settings.state_dir, trigger_id, run_id, self._get_session_async
        )
        await self.announce_run(trigger_id, run)

    def track_background(self, task: asyncio.Task[Any]) -> None:
        # The event loop only holds weak references to tasks -- without a
        # strong one here, a run could be garbage-collected mid-flight.
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def delete_run_threads(self, runs: list[ScheduledRun]) -> None:
        for run in runs:
            await self._delete_thread_data(run.thread_id)

    async def sweep_orphaned_run_threads(self) -> int:
        """Delete run conversations no task still lists -- left behind by
        paths with no checkpointer to delete through (the model's
        delete_scheduled_task, `coscribe --check-wakes` pruning old runs).
        Thread ids are read before the store: a run is recorded before its
        conversation exists, so one starting concurrently (a CLI poll) is
        never mistaken for an orphan."""
        checkpointer = self._checkpointer()
        await checkpointer.setup()  # see list_threads' identical comment
        cursor = await checkpointer.conn.execute(
            "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE ?",
            (f"{SCHEDULED_THREAD_PREFIX}%",),
        )
        thread_ids = [row[0] for row in await cursor.fetchall()]
        known = {
            run.thread_id
            for trigger in ScheduledTriggerStore(self._settings.state_dir).list_all()
            for run in trigger.runs
        }
        orphans = [t for t in thread_ids if t not in known]
        for thread_id in orphans:
            await self._delete_thread_data(thread_id)
        return len(orphans)
