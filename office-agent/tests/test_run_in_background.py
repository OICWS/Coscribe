import sys
import threading
import time
from functools import partial
from pathlib import Path

from coscribe.tools import (
    BackgroundTaskStore,
    Detachable,
    adopt_running_command,
    read_background_log,
    request_detach,
    set_change_listener,
    stop_background_task,
)
from coscribe.tools.exec.running import _RUNNING, Ran, run_to_end

_SLOW = (
    "import sys, time\n"
    "print('first', flush=True)\n"
    "time.sleep(0.3)\n"
    "print('oops', file=sys.stderr, flush=True)\n"
    "time.sleep({seconds})\n"
    "print('last', flush=True)\n"
)


def _run(code: str, timeout: float, detachable: Detachable | None, scratch: Path) -> Ran:
    return run_to_end(
        [sys.executable, "-c", code],
        str(scratch),
        {},
        timeout,
        language="python",
        description="slow",
        script=code,
        scratch_dir=scratch,
        detachable=detachable,
    )


def _in_thread(code: str, timeout: float, detachable: Detachable | None, scratch: Path):
    box: list[Ran] = []
    worker = threading.Thread(target=lambda: box.append(_run(code, timeout, detachable, scratch)))
    worker.start()
    return worker, box


def _until(check, seconds: float = 20.0) -> None:
    deadline = time.monotonic() + seconds
    while not check():
        assert time.monotonic() < deadline, "timed out waiting"
        time.sleep(0.05)


def _printed_first(thread_id: str, code: str) -> bool:
    # A loaded machine can take a while to start the interpreter; detach once it has printed.
    command = _RUNNING.get((thread_id, code))
    return command is not None and "first" in command.stdout_text()


def test_a_command_that_ends_returns_its_two_streams_apart(tmp_path: Path) -> None:
    ran = _run(_SLOW.format(seconds=0), 30, None, tmp_path)
    assert ran.returncode == 0
    assert ran.stdout == "first\nlast\n"
    assert ran.stderr == "oops\n"


def test_a_timeout_keeps_the_output_so_far(tmp_path: Path) -> None:
    ran = _run(_SLOW.format(seconds=30), 1.5, None, tmp_path)
    assert ran.timed_out
    assert ran.stdout == "first\n"


def test_detaching_hands_the_process_to_the_background_store(tmp_path: Path) -> None:
    state = tmp_path / "state"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    heard: list[str] = []
    set_change_listener("t1", lambda task: heard.append(task.status))
    detachable = Detachable("t1", partial(adopt_running_command, state))
    code = _SLOW.format(seconds=2)
    worker, box = _in_thread(code, 60, detachable, scratch)
    _until(lambda: _printed_first("t1", code))
    assert request_detach("t1", code, None)
    worker.join(10)
    assert not worker.is_alive()

    detached = box[0].detached
    assert detached is not None
    assert detached["status"] == "running_in_background"
    task_id = str(detached["task_id"])
    assert "first" in str(detached["output_so_far"])
    assert scratch.exists()  # the process still needs it

    # The listener hears of the end after the record is saved, so wait for the later of the two.
    _until(lambda: heard[-1:] == ["succeeded"])
    log = read_background_log(state, task_id)
    assert log is not None
    # One log, in the order it was written, across both streams.
    assert log["output"].split() == ["first", "oops", "last"]
    assert not scratch.exists()
    assert heard[0] == "running"


def test_a_detached_command_can_be_stopped(tmp_path: Path) -> None:
    state = tmp_path / "state"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    detachable = Detachable("t2", partial(adopt_running_command, state))
    code = _SLOW.format(seconds=60)
    worker, box = _in_thread(code, 60, detachable, scratch)
    _until(lambda: _printed_first("t2", code))
    assert request_detach("t2", code, None)
    worker.join(10)
    detached = box[0].detached
    assert detached is not None
    task_id = str(detached["task_id"])
    stop_background_task(state, task_id, "t2")
    store = BackgroundTaskStore(state)
    _until(lambda: getattr(store.load(task_id), "finished_at", None) is not None)
    task = store.load(task_id)
    assert task is not None and task.status == "killed"


def test_only_the_conversation_that_runs_a_script_can_detach_it(tmp_path: Path) -> None:
    detachable = Detachable("t3", partial(adopt_running_command, tmp_path / "state"))
    code = _SLOW.format(seconds=1)
    worker, box = _in_thread(code, 30, detachable, tmp_path)
    _until(lambda: _printed_first("t3", code))
    assert not request_detach("another-conversation", code, None)
    assert not request_detach("t3", "print('a different script')", None)
    worker.join(10)
    assert box[0].returncode == 0
    assert not request_detach("t3", code, None)  # it has ended


def test_without_a_way_to_hand_over_there_is_nothing_to_detach(tmp_path: Path) -> None:
    code = _SLOW.format(seconds=1)
    worker, box = _in_thread(code, 30, None, tmp_path)
    time.sleep(0.3)
    assert not request_detach("t4", code, None)
    worker.join(10)
    assert box[0].returncode == 0


def test_stopping_a_conversation_ends_the_script_its_tool_call_waits_on(tmp_path: Path) -> None:
    from coscribe.tools import stop_commands

    detachable = Detachable("t5", partial(adopt_running_command, tmp_path / "state"))
    code = _SLOW.format(seconds=60)
    worker, box = _in_thread(code, 120, detachable, tmp_path)
    _until(lambda: _printed_first("t5", code))
    stop_commands("another-conversation")
    assert worker.is_alive()  # only the stopped conversation's scripts end
    started = time.monotonic()
    stop_commands("t5")
    worker.join(15)
    assert not worker.is_alive() and time.monotonic() - started < 15
    assert box[0].detached is None and box[0].returncode != 0
    assert box[0].stdout == "first\n"
