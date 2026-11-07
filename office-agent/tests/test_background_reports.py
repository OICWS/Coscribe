"""A background script's or command's end comes back to its conversation by itself, the way a
background sub-agent's does, so the model carries on without polling or asking to be woken."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from coscribe.conversation.subagents import BACKGROUND_REPORT_PREFIX, SubAgentReporter
from coscribe.conversation.turn_lock import TurnLock
from coscribe.tools.bookkeeping.background_tasks import BackgroundTask, BackgroundTaskStore
from coscribe.tools.bookkeeping.selfwake import WakeRequest, WakeStore


class _Host:
    """The parts of a conversation a report reads and calls."""

    def __init__(self, state_dir: Path) -> None:
        self.thread_id = "t1"
        self.settings = SimpleNamespace(state_dir=state_dir)
        self._live_websocket: Any = None
        self._turn_lock = TurnLock(lambda _busy: None)
        self._current_turn_task: Any = None
        self._reporting_subagents: set[str] = set()
        self._report_tasks: set[asyncio.Task[None]] = set()
        self._report_turns_in_row = 0
        self.turns: list[str] = []

    def is_workflow_run(self) -> bool:
        return False

    async def notify_resync(self) -> None:
        return None

    async def _handle_user_message_locked(self, text: str, websocket: Any, **_: Any) -> None:
        self.turns.append(text)


def _finished(
    store: BackgroundTaskStore, task_id: str, status: str, **fields: Any
) -> BackgroundTask:
    task = BackgroundTask(
        task_id=task_id,
        thread_id="t1",
        language="python",
        description="count the rows",
        status=status,
        started_at=datetime.now(UTC).isoformat(),
        exit_code=fields.pop("exit_code", 0),
        **fields,
    )
    store.save(task)
    return task


def _load(store: BackgroundTaskStore, task_id: str) -> BackgroundTask:
    task = store.load(task_id)
    assert task is not None
    return task


async def _ended(host: _Host, task: BackgroundTask) -> None:
    SubAgentReporter(cast(Any, host))._background_task_changed(task)
    await asyncio.gather(*host._report_tasks)


async def test_a_finished_script_reports_its_outcome_and_output_as_a_turn(tmp_path: Path) -> None:
    store = BackgroundTaskStore(tmp_path)
    task = _finished(store, "a1", "succeeded")
    store.log_path("a1").write_text("rows: 20000\n", encoding="utf-8")

    first, again = _Host(tmp_path), _Host(tmp_path)

    await _ended(first, task)
    await _ended(again, _load(store, "a1"))

    [turn] = first.turns
    assert "(task a1) finished. The end of its output:" in turn and "rows: 20000" in turn
    assert again.turns == []
    assert _load(store, "a1").reported


async def test_the_report_names_the_task_its_outcome_and_the_end_of_its_output(
    tmp_path: Path,
) -> None:
    store = BackgroundTaskStore(tmp_path)
    store.log_path("b1").parent.mkdir(parents=True, exist_ok=True)
    store.log_path("b1").write_text("Traceback...\nKeyError: 'region'\n", encoding="utf-8")
    host = _Host(tmp_path)

    await _ended(host, _finished(store, "b1", "failed", exit_code=1))

    [turn] = host.turns
    assert turn.startswith(f'{BACKGROUND_REPORT_PREFIX} "count the rows" (task b1) failed')
    assert "exit code 1" in turn and "KeyError: 'region'" in turn


async def test_a_task_the_model_already_read_or_stopped_is_not_reported(tmp_path: Path) -> None:
    store = BackgroundTaskStore(tmp_path)
    host = _Host(tmp_path)

    await _ended(host, _finished(store, "c1", "succeeded", reported=True))
    await _ended(host, _finished(store, "c2", "running"))

    assert host.turns == []


async def test_a_pending_wake_on_the_task_is_taken_and_its_reason_goes_with_the_report(
    tmp_path: Path,
) -> None:
    store = BackgroundTaskStore(tmp_path)
    wakes = WakeStore(tmp_path)
    wakes.save(
        WakeRequest(
            wake_id="w1",
            thread_id="t1",
            kind="task",
            reason="summarize the totals",
            created_at=datetime.now(UTC).isoformat(),
            task_id="d1",
        )
    )
    host = _Host(tmp_path)

    await _ended(host, _finished(store, "d1", "killed"))

    [turn] = host.turns
    assert "was stopped by the user" in turn and "It printed nothing." in turn
    assert "summarize the totals" in turn
    assert wakes.list_pending() == []
