"""A task that starts on something new in a connector (decision 0039): what counts as new, what an
item fills in, the limits on the runs it starts, and the checks the poll makes."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.tools import StructuredTool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from coscribe.runtime import tool_metadata
from coscribe.runtime_lg import poll_due_scheduled_tasks
from coscribe.runtime_lg.audit import AuditLog
from coscribe.tools.bookkeeping import ScheduleRule
from coscribe.tools.bookkeeping.connector_items import (
    MAX_RUNNING,
    ConnectorItems,
    event_inputs,
    item_key,
    items_of,
    room,
)
from coscribe.tools.bookkeeping.scheduled_run import ScheduledRun
from coscribe.tools.bookkeeping.scheduled_tasks import (
    ScheduledTriggerStore,
    create_trigger,
    patch_trigger,
)
from coscribe.workflow_spec import parse_workflow

from .test_scheduled_tasks_resume import FakeToolCallingChatModel, _make_get_session, _settings

_INVOICE_TASK = {
    "inputs": [
        {"name": "amount", "label": "Amount", "type": "number"},
        {"name": "sender", "label": "From", "type": "text", "required": False},
        {"name": "mail", "label": "Whole message", "type": "text", "required": False},
    ],
    "steps": [
        {
            "id": "log",
            "title": "Log it",
            "kind": "tool",
            "tool": "write_file",
            "args": {"path": "seen-{{amount}}.txt", "content": "{{sender}}"},
        }
    ],
}
_SPECS = list(parse_workflow(_INVOICE_TASK).inputs)


def _connector_tool(answer: list[Any], *, read_only: bool = True) -> Any:
    def search(query: str = "") -> str:
        return json.dumps({"messages": answer})

    tool = StructuredTool.from_function(
        search, name="mail_search", description="Search mail", metadata={"readOnlyHint": read_only}
    )
    tool_metadata(tool, risk_category="EXTERNAL", category="mcp:mail")
    return tool


def _mail(n: int, amount: Any = 10) -> dict[str, Any]:
    return {
        "id": f"m{n}",
        "subject": f"Invoice {n}",
        "amount": amount,
        "from": {"email": f"a{n}@example.com"},
    }


def test_the_list_in_an_answer_and_what_names_an_item() -> None:
    assert items_of([1, 2]) == [1, 2]
    assert items_of({"messages": [1], "next": "x"}) == [1]
    assert items_of({"found": [3], "total": 1}) == [3]
    assert items_of({"a": [1], "b": [2]}) is None
    assert items_of("text") is None
    assert item_key({"id": 7, "subject": "x"}) == "id:7"
    assert item_key({"url": "https://x.example/1"}) == "url:https://x.example/1"
    # Without a field naming it, an item is known by all of it.
    assert item_key({"a": 1, "b": 2}) == item_key({"b": 2, "a": 1}) != item_key({"a": 1})


def test_an_item_fills_inputs_by_name_by_choice_or_whole() -> None:
    mail = _mail(1, amount="12.50")
    today = date(2026, 11, 8)
    # "amount" is filled by the field of its name; nothing is named like "sender" or "From".
    assert event_inputs(_SPECS, {}, mail, today) == {"amount": 12.5, "sender": "", "mail": ""}
    with pytest.raises(ValueError, match="Amount takes one value, and from holds more"):
        event_inputs(_SPECS, {"amount": "from"}, mail, today)
    filled = event_inputs(_SPECS, {"sender": "from.email", "mail": "*"}, mail, today)
    assert filled["amount"] == 12.5 and filled["sender"] == "a1@example.com"
    assert json.loads(filled["mail"]) == mail
    # "" leaves an input to its default.
    assert event_inputs(_SPECS, {"sender": "", "mail": ""}, mail, today)["sender"] == ""
    with pytest.raises(ValueError, match="Amount needs a number"):
        event_inputs(_SPECS, {"sender": ""}, _mail(2, amount="soon"), today)
    with pytest.raises(ValueError, match="Amount needs a value"):
        event_inputs(_SPECS, {"sender": ""}, {"id": "m3"}, today)


def test_new_items_start_runs_once_within_the_limits(tmp_path: Path) -> None:
    items = ConnectorItems(tmp_path)
    rule = ScheduleRule(
        kind="connector",
        at="",
        minutes=5,
        tool="mail_search",
        args={"query": "label:invoices"},
        inputs_from={"sender": "from.email"},
    )
    # The first look takes what is there as seen.
    assert items.take("t1", rule, _SPECS, [], [_mail(1)]) == (
        [],
        "First look: 1 items taken as seen",
    )
    answer = [_mail(n) for n in range(1, 9)] + [_mail(9, amount="soon")]
    starting, summary = items.take("t1", rule, _SPECS, [], answer)
    # No more start than may run at once.
    assert [key for key, _, _ in starting] == [f"id:m{n}" for n in range(2, 2 + MAX_RUNNING)]
    assert summary == "8 new: 3 started, 1 refused, 4 held"
    shown = items.shown("t1")
    assert shown["missed"][0]["item"] == "Invoice 9"
    assert "Amount needs a number" in shown["missed"][0]["reason"]
    # What was held comes at the next check; what was started or refused doesn't.
    starting, _ = items.take("t1", rule, _SPECS, [], answer)
    assert [key for key, _, _ in starting] == ["id:m5", "id:m6", "id:m7"]
    assert [key for key, _, _ in items.take("t1", rule, _SPECS, [], answer)[0]] == ["id:m8"]
    assert items.take("t1", rule, _SPECS, [], answer) == ([], "")
    # Asking something else starts over.
    rule.args = {"query": "label:receipts"}
    assert items.take("t1", rule, _SPECS, [], answer)[0] == []


def test_room_counts_the_hour_and_the_runs_going() -> None:
    now = datetime(2026, 11, 8, 12, 0)

    def run(minutes_ago: int, status: str = "completed", source: str = "connector") -> Any:
        started = (now - timedelta(minutes=minutes_ago)).isoformat()
        return ScheduledRun(
            run_id="r", thread_id="t", started_at=started, source=source, status=status
        )

    assert room([], 30, now) == MAX_RUNNING
    assert room([run(10) for _ in range(28)], 30, now) == 2
    assert room([run(90) for _ in range(40)], 30, now) == MAX_RUNNING
    assert room([run(1, "running"), run(2)], 30, now) == MAX_RUNNING - 1
    assert room([run(1, "running", source="manual") for _ in range(3)], 30, now) == MAX_RUNNING


def test_a_connector_task_names_its_tool_and_real_inputs(tmp_path: Path) -> None:
    store = ScheduledTriggerStore(tmp_path)
    base: dict[str, Any] = {"name": "Invoices", "kind": "connector", "at": ""}
    for workflow, watch, problem in [
        (None, {"minutes": 5, "tool": "mail_search"}, "Only a task with steps"),
        (_INVOICE_TASK, {"minutes": 5}, "names the tool"),
        (_INVOICE_TASK, {"minutes": 2, "tool": "mail_search"}, "minutes must be 5-1440"),
        (_INVOICE_TASK, {"minutes": 5, "tool": "t", "inputs_from": {"x": "id"}}, "no input 'x'"),
        (_INVOICE_TASK, {"minutes": 5, "tool": "t", "per_hour": 500}, "1 to 120 runs"),
    ]:
        with pytest.raises(ValueError, match=problem):
            create_trigger(store, **base, prompt="p", workflow=workflow, watch=watch)
    trigger = create_trigger(
        store,
        **base,
        prompt="",
        workflow=_INVOICE_TASK,
        watch={"minutes": 10, "tool": "mail_search", "args": {"query": "q"}},
    )
    assert trigger.next_run_at is not None and trigger.schedule.per_hour == 30
    # An edit that changes something else keeps what it asks.
    renamed = patch_trigger(store, trigger.trigger_id, {"name": "Bills"})
    assert renamed.schedule.tool == "mail_search" and renamed.schedule.args == {"query": "q"}


def _due(store: ScheduledTriggerStore, trigger_id: str) -> None:
    trigger = store.load(trigger_id)
    assert trigger is not None
    trigger.next_run_at = (datetime.now() - timedelta(minutes=1)).isoformat()
    store.save(trigger)


async def test_the_poll_asks_the_connector_and_starts_a_run_per_new_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    settings.workspace_root.mkdir()
    store = ScheduledTriggerStore(settings.state_dir)
    watch = {
        "minutes": 5,
        "tool": "mail_search",
        "args": {"query": "label:invoices"},
        "inputs_from": {"sender": "from.email", "mail": ""},
    }
    trigger = create_trigger(
        store,
        name="Invoices",
        kind="connector",
        at="",
        prompt="",
        workflow=_INVOICE_TASK,
        watch=watch,
    )
    answer = [_mail(1)]
    tools = [_connector_tool(answer)]
    ended: list[str] = []

    async def on_ended(trigger_id: str, run: Any) -> None:
        ended.append(run.status)

    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "cp.sqlite")) as checkpointer:
        get_session = await _make_get_session(
            settings, checkpointer, FakeToolCallingChatModel(responses=[]), monkeypatch
        )

        async def poll() -> list[Any]:
            _due(store, trigger.trigger_id)
            return await poll_due_scheduled_tasks(
                settings.state_dir, get_session, on_ended=on_ended, connector_tools=lambda: tools
            )

        assert await poll() == []  # the first look
        answer.insert(0, _mail(2, amount=42))
        assert await poll() == []
        # Not due: no check.
        answer.insert(0, _mail(3))
        await poll_due_scheduled_tasks(
            settings.state_dir, get_session, connector_tools=lambda: tools
        )

    saved = store.load(trigger.trigger_id)
    assert saved is not None and ended == ["completed"] and len(saved.runs) == 1
    run = saved.runs[0]
    assert run.source == "connector" and run.inputs == {
        "amount": 42,
        "sender": "a2@example.com",
        "mail": "",
    }
    assert run.event == {
        "connector": "mail",
        "tool": "mail_search",
        "key": "id:m2",
        "item": _mail(2, amount=42),
    }
    assert (settings.workspace_root / "seen-42.txt").read_text(encoding="utf-8") == "a2@example.com"
    assert saved.next_run_at is not None and saved.next_run_at > datetime.now().isoformat()
    checks = [e for e in AuditLog(settings.state_dir).read_all() if e.reason == "trigger_check"]
    assert [e.detail for e in checks] == [
        "First look: 1 items taken as seen",
        "1 new: 1 started, 0 refused, 0 held",
    ]
    assert checks[0].tool_name == "mail_search" and checks[0].arguments == watch["args"]


async def test_a_tool_not_marked_read_only_or_not_there_is_not_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    store = ScheduledTriggerStore(settings.state_dir)
    trigger = create_trigger(
        store,
        name="Invoices",
        kind="connector",
        at="",
        prompt="",
        workflow=_INVOICE_TASK,
        watch={"minutes": 5, "tool": "mail_search"},
    )
    asked: list[str] = []
    unmarked = _connector_tool([_mail(1)], read_only=False)
    unmarked.func = lambda query="": asked.append(query) or "[]"

    async def get_session(thread_id: str) -> Any:
        raise AssertionError("no run starts")

    for tools, problem in [([], "isn't available"), ([unmarked], "isn't marked read-only")]:
        _due(store, trigger.trigger_id)
        await poll_due_scheduled_tasks(
            settings.state_dir, get_session, connector_tools=lambda tools=tools: tools
        )
        assert problem in (store.connector_items.shown(trigger.trigger_id)["last_check"]["error"])
    assert asked == []
    # Once the person confirms it, it is asked.
    patch_trigger(
        store,
        trigger.trigger_id,
        {"watch": {"minutes": 5, "tool": "mail_search", "trust_unmarked": True}},
    )
    _due(store, trigger.trigger_id)
    await poll_due_scheduled_tasks(
        settings.state_dir, get_session, connector_tools=lambda: [unmarked]
    )
    assert asked == [""]
    # A paused task starts from what is there when it resumes.
    paused = store.load(trigger.trigger_id)
    assert paused is not None
    paused.enabled = False
    store.save(paused)
    await poll_due_scheduled_tasks(settings.state_dir, get_session, connector_tools=lambda: [])
    assert store.connector_items.read(trigger.trigger_id) == {}
