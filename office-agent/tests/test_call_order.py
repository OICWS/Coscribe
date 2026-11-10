"""An answer's `task_create` calls run in the order the model wrote them (runtime_lg/call_order)."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver

from coscribe.runtime_lg import call_order
from coscribe.runtime_lg.agent import build_langgraph_agent
from coscribe.runtime_lg.call_order import CallOrderMiddleware
from coscribe.tools.bookkeeping.tasks import TaskToolkit, build_task_tools

_NAMES = [f"read report{n}.txt" for n in range(1, 9)]


class _Model(BaseChatModel):
    responses: list[AIMessage]
    i: int = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        message = self.responses[self.i]
        self.i += 1
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "call-order-model"


def _plan_in_one_answer() -> _Model:
    calls = [
        {"name": "task_create", "args": {"content": name}, "id": f"c{n}"}
        for n, name in enumerate(_NAMES)
    ]
    return _Model(responses=[AIMessage(content="", tool_calls=calls), AIMessage(content="ok")])


def _tools_where_a_later_call_is_faster(tmp_path: Path) -> list[Any]:
    """Without an order kept, the last call of the answer would finish first."""
    real = build_task_tools("t1", tmp_path)[0]

    def task_create(content: str) -> dict[str, Any]:
        """Add a task to the plan."""
        time.sleep(0.02 * (len(_NAMES) - _NAMES.index(content)))
        return real(content)

    return [task_create]


def _plan(tmp_path: Path) -> list[tuple[str, str]]:
    return [(task["id"], task["content"]) for task in TaskToolkit("t1", tmp_path).list_tasks()]


_IN_ORDER = [(str(n), name) for n, name in enumerate(_NAMES, start=1)]
_CONFIG: Any = {"configurable": {"thread_id": "t1"}}
_ASK = {"messages": [HumanMessage(content="plan it")]}


def test_tasks_made_in_one_answer_get_their_ids_in_the_order_written(tmp_path: Path) -> None:
    agent = build_langgraph_agent(
        _plan_in_one_answer(),
        _tools_where_a_later_call_is_faster(tmp_path),
        "be helpful",
        checkpointer=InMemorySaver(),
    )

    agent.invoke(_ASK, config=_CONFIG)

    assert _plan(tmp_path) == _IN_ORDER


async def test_the_order_is_kept_on_the_async_path_too(tmp_path: Path) -> None:
    agent = build_langgraph_agent(
        _plan_in_one_answer(),
        _tools_where_a_later_call_is_faster(tmp_path),
        "be helpful",
        checkpointer=InMemorySaver(),
    )

    await agent.ainvoke(_ASK, config=_CONFIG)

    assert _plan(tmp_path) == _IN_ORDER


def _request(call_id: str, name: str, calls: list[dict[str, Any]]) -> SimpleNamespace:
    state = {"messages": [AIMessage(content="", tool_calls=calls)]}
    return SimpleNamespace(tool_call={"name": name, "id": call_id, "args": {}}, state=state)


async def test_other_tools_of_the_answer_do_not_wait() -> None:
    calls = [
        {"name": "task_create", "args": {}, "id": "a"},
        {"name": "read_file", "args": {}, "id": "b"},
    ]
    order = CallOrderMiddleware()
    held = asyncio.Event()

    async def slow(request: Any) -> str:
        await held.wait()
        return "created"

    async def fast(request: Any) -> str:
        return "read"

    first = asyncio.create_task(order.awrap_tool_call(_request("a", "task_create", calls), slow))
    assert await order.awrap_tool_call(_request("b", "read_file", calls), fast) == "read"
    held.set()
    assert await first == "created"


async def test_a_call_that_fails_lets_the_next_one_run() -> None:
    calls = [{"name": "task_create", "args": {}, "id": c} for c in ("a", "b")]
    order = CallOrderMiddleware()

    async def fails(request: Any) -> str:
        raise ValueError("no")

    async def works(request: Any) -> str:
        return "created"

    second = asyncio.create_task(order.awrap_tool_call(_request("b", "task_create", calls), works))
    with pytest.raises(ValueError):
        await order.awrap_tool_call(_request("a", "task_create", calls), fails)
    assert await second == "created"
    assert order._ended == {}


def test_a_call_whose_predecessor_never_runs_goes_ahead_after_the_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(call_order, "_WAIT_SECONDS", 0.05)
    calls = [{"name": "task_create", "args": {}, "id": c} for c in ("a", "b")]
    order = CallOrderMiddleware()

    assert order.wrap_tool_call(_request("b", "task_create", calls), lambda _: "created") == (
        "created"
    )


def test_two_threads_never_get_the_same_task_id(tmp_path: Path) -> None:
    toolkit = TaskToolkit("t2", tmp_path)
    threads = [
        threading.Thread(target=lambda: [toolkit.create("x") for _ in range(50)]) for _ in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    ids = [task["id"] for task in toolkit.list_tasks()]
    assert len(set(ids)) == len(ids) == 400
