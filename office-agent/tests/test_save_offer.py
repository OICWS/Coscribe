"""The offer to save a turn's job as a workflow or skill: which turns qualify, and once only."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from coscribe.conversation.save_offer import (
    MIN_STEPS,
    SaveOffer,
    changing_steps,
    clean_name,
    this_turn,
)
from coscribe.runtime import ToolMetadata

CATALOG = {
    "read_file": ToolMetadata(risk_category="READ"),
    "write_file": ToolMetadata(risk_category="WRITE_LOCAL"),
    "task_create": ToolMetadata(risk_category="READ"),
}


def _turn(*calls: tuple[str, dict[str, Any], str, str]) -> list[BaseMessage]:
    """An AI message per call, each followed by its result: (name, args, result, status)."""
    messages: list[BaseMessage] = []
    for i, (name, args, result, status) in enumerate(calls):
        messages.append(
            AIMessage(content="", tool_calls=[{"id": f"c{i}", "name": name, "args": args}])
        )
        messages.append(ToolMessage(content=result, tool_call_id=f"c{i}", status=status))
    return messages


def _writes(n: int) -> list[tuple[str, dict[str, Any], str, str]]:
    return [("write_file", {"path": f"out{i}.txt"}, "ok", "success") for i in range(n)]


def test_only_succeeded_changes_count() -> None:
    script = json.dumps({"files_written": ["chart.png"]})
    idle_script = json.dumps({"files_written": []})
    messages = _turn(
        ("read_file", {"path": "in.txt"}, "data", "success"),
        ("write_file", {"path": "a.txt"}, "ok", "success"),
        ("write_file", {"path": "b.txt"}, "denied", "error"),
        ("run_python_script", {"script": "..."}, script, "success"),
        ("run_python_script", {"script": "..."}, idle_script, "success"),
    )
    assert changing_steps(messages, CATALOG) == ["write_file a.txt", "run_python_script"]


def test_this_turn_starts_after_the_last_message_of_the_person() -> None:
    earlier = _turn(*_writes(5))
    later = _turn(("write_file", {"path": "x.txt"}, "ok", "success"))
    messages = [HumanMessage(content="one"), *earlier, HumanMessage(content="two"), *later]
    assert this_turn(messages) == later


def test_clean_name() -> None:
    assert clean_name('"Weekly sales report."\nmore') == "Weekly sales report"
    assert clean_name("NONE") == "" and clean_name("") == "" and clean_name("x" * 80) == ""


class _Model:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls = 0

    async def ainvoke(self, messages: list[Any], config: Any = None) -> AIMessage:
        self.calls += 1
        return AIMessage(content=self.reply)


class _Socket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)


def _host(
    tmp_path: Path, messages: list[BaseMessage], thread_id: str = "t1", on: bool = True
) -> Any:
    class _Agent:
        async def aget_state(self, config: Any) -> Any:
            return SimpleNamespace(values={"messages": messages})

    return SimpleNamespace(
        settings=SimpleNamespace(state_dir=tmp_path, save_offers=on),
        thread_id=thread_id,
        lg_agent=_Agent(),
        config={},
        tool_catalog=lambda: CATALOG,
        _stop_requested=False,
        _pending_approvals={},
        _pending_questions={},
    )


async def _consider(offer: SaveOffer, socket: _Socket) -> None:
    offer.consider(socket, "make the weekly report")
    if offer._task is not None:
        await offer._task


async def test_a_job_of_several_changes_is_offered_once(tmp_path: Path) -> None:
    calls = [("task_create", {"content": "plan"}, "ok", "success"), *_writes(MIN_STEPS)]
    messages = [HumanMessage(content="make the weekly report"), *_turn(*calls)]
    model, socket = _Model("Weekly report"), _Socket()
    offer = SaveOffer(_host(tmp_path, messages), lambda: model)

    await _consider(offer, socket)
    await _consider(offer, socket)

    # The task bookkeeping isn't a step the person would count.
    assert socket.sent == [{"type": "save_offer", "steps": MIN_STEPS, "name": "Weekly report"}]
    assert model.calls == 1
    # Once per conversation, also after a restart.
    again = SaveOffer(_host(tmp_path, messages), lambda: model)
    await _consider(again, socket)
    assert len(socket.sent) == 1


async def test_no_offer_for_a_short_turn_a_one_off_a_run_a_stop_or_when_off(tmp_path: Path) -> None:
    short = [HumanMessage(content="fix it"), *_turn(*_writes(MIN_STEPS - 1))]
    long = [HumanMessage(content="fix it"), *_turn(*_writes(MIN_STEPS))]
    cases = [
        (_host(tmp_path, short, "a"), "Fix"),
        (_host(tmp_path, long, "b"), "NONE"),
        (_host(tmp_path, long, "scheduled-trig-run1"), "Weekly"),
        (_host(tmp_path, long, "c", on=False), "Weekly"),
        (_host(tmp_path, long, "d"), "Weekly"),
    ]
    # Stopped by the person: what it did isn't the job they asked for.
    cases[-1][0]._stop_requested = True
    for host, reply in cases:
        model, socket = _Model(reply), _Socket()
        await _consider(SaveOffer(host, lambda m=model: m), socket)
        assert socket.sent == [], host.thread_id
    assert not list(tmp_path.glob("*.save-offered"))
