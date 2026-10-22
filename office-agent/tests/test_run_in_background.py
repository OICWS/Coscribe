import sys
import threading
import time
from functools import partial
from pathlib import Path

from coscribe.tools import (
    BackgroundTaskStore,
    adopt_running_command,
    read_background_log,
    request_detach,
    set_change_listener,
    stop_background_task,
    tool_call_id,
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


def _run(code: str, timeout: float, hand_off, scratch: Path, call_id: str | None) -> Ran:
    def go() -> Ran:
        return run_to_end(
            [sys.executable, "-c", code],
            str(scratch),
            {},
            timeout,
            language="python",
            description="slow",
            scratch_dir=scratch,
            hand_off=hand_off,
        )

    if call_id is None:
        return go()
    with tool_call_id(call_id):
        return go()


def _until(check, seconds: float = 20.0) -> None:
    deadline = time.monotonic() + seconds
    while not check():
        assert time.monotonic() < deadline, "timed out waiting"
        time.sleep(0.05)


def test_a_command_that_ends_returns_its_two_streams_apart(tmp_path: Path) -> None:
    ran = _run(_SLOW.format(seconds=0), 30, None, tmp_path, None)
    assert ran.returncode == 0
    assert ran.stdout == "first\nlast\n"
    assert ran.stderr == "oops\n"


def test_a_timeout_keeps_the_output_so_far(tmp_path: Path) -> None:
    ran = _run(_SLOW.format(seconds=30), 1.5, None, tmp_path, None)
    assert ran.timed_out
    assert ran.stdout == "first\n"


def test_detaching_hands_the_process_to_the_background_store(tmp_path: Path) -> None:
    state = tmp_path / "state"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    heard: list[str] = []
    set_change_listener("t1", lambda task: heard.append(task.status))
    hand_off = partial(adopt_running_command, state, "t1")
    box: list[Ran] = []
    worker = threading.Thread(
        target=lambda: box.append(_run(_SLOW.format(seconds=2), 60, hand_off, scratch, "call-1"))
    )
    worker.start()
    # The button can only land once the command is waiting under its call id.
    # A loaded machine can take a while to start the interpreter; detach once it has printed.
    _until(lambda: "call-1" in _RUNNING and "first" in _RUNNING["call-1"].stdout_text())
    assert request_detach("call-1", None)
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
    assert heard[0] == "running" and heard[-1] == "succeeded"


def test_a_detached_command_can_be_stopped(tmp_path: Path) -> None:
    state = tmp_path / "state"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    hand_off = partial(adopt_running_command, state, "t2")
    box: list[Ran] = []
    worker = threading.Thread(
        target=lambda: box.append(_run(_SLOW.format(seconds=60), 60, hand_off, scratch, "call-2"))
    )
    worker.start()
    _until(lambda: request_detach("call-2", None))
    worker.join(10)
    detached = box[0].detached
    assert detached is not None
    task_id = str(detached["task_id"])
    stop_background_task(state, task_id, "t2")
    store = BackgroundTaskStore(state)
    _until(lambda: getattr(store.load(task_id), "finished_at", None) is not None)
    task = store.load(task_id)
    assert task is not None and task.status == "killed"


def test_without_a_way_to_hand_over_there_is_nothing_to_detach(tmp_path: Path) -> None:
    box: list[Ran] = []
    worker = threading.Thread(
        target=lambda: box.append(_run(_SLOW.format(seconds=1), 30, None, tmp_path, "call-3"))
    )
    worker.start()
    time.sleep(0.3)
    assert not request_detach("call-3", None)
    worker.join(10)
    assert box[0].returncode == 0


def _agent_that_calls(tool, call_id: str):
    from langchain_core.messages import AIMessage
    from langgraph.checkpoint.memory import InMemorySaver

    from coscribe.runtime_lg.agent import build_langgraph_agent
    from tests.test_runtime_lg_agent import _FakeModel

    model = _FakeModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": tool.__name__, "args": {}, "id": call_id}]),
            AIMessage(content="done"),
        ]
    )
    return build_langgraph_agent(model, [tool], "be helpful", checkpointer=InMemorySaver())


def test_a_sync_tool_finds_its_call_id_in_a_streamed_turn() -> None:
    import asyncio

    from langchain_core.messages import HumanMessage

    from coscribe.tools.exec.running import _CALL_ID

    seen: list[str | None] = []

    def probe() -> str:
        """Reads the bound call id."""
        seen.append(_CALL_ID.get())
        return "ok"

    agent = _agent_that_calls(probe, "call-xyz")
    config = {"configurable": {"thread_id": "t"}}

    async def go() -> None:
        async for _ in agent.astream({"messages": [HumanMessage(content="go")]}, config=config):
            pass

    asyncio.run(go())
    assert seen == ["call-xyz"]
    assert _CALL_ID.get() is None


def test_a_sync_tool_finds_its_call_id_in_a_blocking_turn() -> None:
    from langchain_core.messages import HumanMessage

    from coscribe.tools.exec.running import _CALL_ID

    seen: list[str | None] = []

    def probe() -> str:
        """Reads the bound call id."""
        seen.append(_CALL_ID.get())
        return "ok"

    agent = _agent_that_calls(probe, "call-abc")
    agent.invoke(
        {"messages": [HumanMessage(content="go")]}, config={"configurable": {"thread_id": "t"}}
    )
    assert seen == ["call-abc"]
