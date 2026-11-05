"""The end-of-turn plan check and the repeated-call note (runtime_lg/turn_checks.py), through a
real agent graph with a scripted model."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver

from coscribe.runtime import tool_metadata
from coscribe.runtime_lg.agent import build_langgraph_agent
from coscribe.runtime_lg.messages import (
    is_plan_check,
    plan_check_message,
    serialize_history_for_ws_lg,
    starts_a_turn,
)
from coscribe.runtime_lg.turn_checks import REPEAT_NOTE, repeats_earlier_call


class _Model(BaseChatModel):
    responses: list[AIMessage]
    seen: list[list[BaseMessage]] = []
    i: int = 0

    def bind_tools(self, tools: Any, *, tool_choice: str | None = None, **kwargs: Any) -> Any:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.seen.append(list(messages))
        message = self.responses[self.i]
        self.i += 1
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "fake-turn-checks-model"


def _call(call_id: str, name: str, **args: Any) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"id": call_id, "name": name, "args": args}])


def _run(model: _Model, tools: list[Any], open_tasks: Any = None, text: str = "go") -> Any:
    agent = build_langgraph_agent(
        model, tools, "be helpful", checkpointer=InMemorySaver(), open_tasks=open_tasks
    )
    config = {"configurable": {"thread_id": "t"}}
    return agent.invoke({"messages": [HumanMessage(content=text)]}, config=config)


def task_update(task_id: str, status: str) -> str:
    """Updates a task."""
    return "ok"


_OPEN = "Open tasks:\n- [pending] 2: Write the memo"


def test_a_turn_that_ends_with_open_tasks_gets_its_plan_back_once() -> None:
    model = _Model(
        responses=[
            _call("c1", "task_update", task_id="1", status="completed"),
            AIMessage(content="Done."),
            AIMessage(content="Still done."),
        ]
    )

    result = _run(model, [task_update], open_tasks=lambda: _OPEN)

    notes = [m for m in result["messages"] if is_plan_check(m)]
    assert model.i == 3
    assert len(notes) == 1
    assert "2: Write the memo" in notes[0].content
    assert "2: Write the memo" in model.seen[2][-1].content
    assert result["messages"][-1].content == "Still done."


def test_a_turn_with_no_open_tasks_ends_when_the_model_stops() -> None:
    model = _Model(
        responses=[_call("c1", "task_update", task_id="1", status="completed"), AIMessage("Done.")]
    )

    result = _run(model, [task_update], open_tasks=lambda: "")

    assert model.i == 2
    assert not any(is_plan_check(m) for m in result["messages"])


def test_tasks_left_open_by_earlier_work_do_not_hold_up_a_turn_that_did_not_touch_them() -> None:
    model = _Model(responses=[AIMessage(content="It is sunny.")])

    result = _run(model, [task_update], open_tasks=lambda: _OPEN, text="weather?")

    assert model.i == 1
    assert not any(is_plan_check(m) for m in result["messages"])


def test_the_plan_check_is_not_a_request_and_the_chat_does_not_show_it() -> None:
    note = plan_check_message("Open tasks: x")
    history = [HumanMessage(content="hi"), AIMessage(content="ok"), note, AIMessage(content="ok2")]

    entries = serialize_history_for_ws_lg(history)

    assert not starts_a_turn(note)
    assert [e["kind"] for e in entries] == ["user", "agent", "agent"]


def read_file(path: str) -> str:
    """Reads a file."""
    return f"text of {path}"


def write_file(path: str, content: str) -> str:
    """Writes a file."""
    return "written"


tool_metadata(read_file, risk_category="READ", category="filesystem")
tool_metadata(write_file, risk_category="WRITE_LOCAL", category="filesystem")


def _results(result: Any) -> list[str]:
    return [m.content for m in result["messages"] if isinstance(m, ToolMessage)]


async def test_the_same_read_again_in_a_turn_is_noted_on_its_result() -> None:
    model = _Model(
        responses=[
            _call("c1", "read_file", path="a.txt"),
            _call("c2", "read_file", path="b.txt"),
            _call("c3", "read_file", path="a.txt"),
            AIMessage(content="done"),
        ]
    )

    agent = build_langgraph_agent(model, [read_file, write_file], "be helpful")
    config = {"configurable": {"thread_id": "t"}}
    results = _results(await agent.ainvoke({"messages": [HumanMessage("go")]}, config=config))

    assert [r.endswith(REPEAT_NOTE) for r in results] == [False, False, True]


def test_a_read_after_a_write_or_in_a_new_turn_is_not_noted() -> None:
    messages: list[Any] = [
        HumanMessage(content="first"),
        _call("c1", "read_file", path="a.txt"),
        HumanMessage(content="second"),
        _call("c2", "read_file", path="a.txt"),
        _call("c3", "write_file", path="a.txt", content="x"),
    ]
    again = {"id": "c4", "name": "read_file", "args": {"path": "a.txt"}}
    changers = {"write_file"}

    assert not repeats_earlier_call(again, messages, changers)
    assert repeats_earlier_call(again, messages[:4], changers)
    assert not repeats_earlier_call(
        {"id": "c2", "name": "read_file", "args": {"path": "a.txt"}}, messages[:4], changers
    )


def test_a_use_tool_call_is_compared_by_the_tool_it_runs() -> None:
    messages: list[Any] = [HumanMessage(content="go"), _call("c1", "read_file", path="a.txt")]
    wrapped = {
        "id": "c2",
        "name": "use_tool",
        "args": {"name": "read_file", "arguments": '{"path": "a.txt"}'},
    }

    assert repeats_earlier_call(wrapped, messages, set())
