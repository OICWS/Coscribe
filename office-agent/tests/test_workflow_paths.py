"""Decision 0031: the kinds of input a run asks for, conditions that hold all together or any one,
a choice of several paths by a value, and a loop that stops early."""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from coscribe.workflow_spec import (
    choose_arm,
    conditions_hold,
    current_shape,
    input_values,
    parse_workflow,
    walk,
    workflow_error,
)
from coscribe.workflow_spec.spec import Condition

from .test_workflow_engine import Harness, _files_harness


def _tool(step_id: str, save_as: str, path: str = "x.txt") -> dict[str, Any]:
    return {"id": step_id, "kind": "tool", "title": step_id.title(), "tool": "read_file",
            "args": {"path": path}, "save_as": save_as}  # fmt: skip


def _choice(**extra: Any) -> dict[str, Any]:
    return {
        "id": "pick", "kind": "choice", "title": "By department", "value": "dept",
        "cases": [{"is": "Sales", "steps": [_tool("sales", "text", "sales.txt")]},
                  {"is": "Finance", "steps": [_tool("finance", "text", "finance.txt")]}],
        "otherwise": [_tool("other", "text", "other.txt")],
        **extra,
    }  # fmt: skip


def _with_choice(*after: dict[str, Any], **choice: Any) -> dict[str, Any]:
    return {
        "inputs": [{"name": "dept", "type": "choice", "options": ["Sales", "Finance", "Ops"]}],
        "steps": [_choice(**choice), *after],
    }


def _cond(left: Any, op: str, right: Any = None) -> Condition:
    data = {"left": {"value": left}, "op": op}
    return Condition.model_validate(data if right is None else {**data, "right": {"value": right}})


# -- inputs


def _inputs(*specs: dict[str, Any]) -> Any:
    return parse_workflow({"inputs": list(specs), "steps": []}).inputs


def test_a_relative_date_is_worked_out_on_the_day_the_run_starts() -> None:
    names = ["today", "yesterday", "week_start", "last_week_start", "last_week_end",
             "month_start", "last_month_start", "last_month_end", "year_start"]  # fmt: skip
    specs = _inputs(*({"name": n, "type": "date", "default": n} for n in names))

    values = input_values(specs, {}, date(2026, 3, 4))  # a Wednesday

    assert list(values.values()) == [
        "2026-03-04", "2026-03-03", "2026-03-02", "2026-02-23", "2026-03-01",
        "2026-03-01", "2026-02-01", "2026-02-28", "2026-01-01",
    ]  # fmt: skip
    january = input_values(specs, {}, date(2026, 1, 15))
    assert (january["last_month_start"], january["last_month_end"]) == ("2025-12-01", "2025-12-31")


def test_a_run_gets_each_input_as_its_kind_takes_it() -> None:
    specs = _inputs(
        {"name": "send", "type": "yes_no", "default": True},
        {"name": "dept", "type": "choice", "options": ["Sales", "Finance"]},
        {"name": "day", "type": "date"},
        {"name": "folder", "type": "folder", "default": "exports"},
    )

    values = input_values(
        specs, {"send": "no", "dept": " finance ", "day": "2026-05-01"}, date.today()
    )

    assert values == {"send": False, "dept": "Finance", "day": "2026-05-01", "folder": "exports"}
    with pytest.raises(ValueError, match="one of Sales, Finance"):
        input_values(specs, {"dept": "Ops", "day": "2026-05-01"}, date.today())
    with pytest.raises(ValueError, match="needs a date"):
        input_values(specs, {"dept": "Sales", "day": "May 1st"}, date.today())
    with pytest.raises(ValueError, match="needs yes or no"):
        input_values(specs, {"send": "maybe", "dept": "Sales", "day": "2026-05-01"}, date.today())


@pytest.mark.parametrize(
    ("spec", "problem"),
    [
        ({"type": "choice"}, "lists its options"),
        ({"type": "choice", "options": ["A", "a"]}, "listed once"),
        ({"type": "choice", "options": ["A"], "default": "B"}, "isn't one of its options"),
        ({"type": "text", "options": ["A"]}, "only a choice has options"),
        ({"type": "date", "default": "next_tuesday"}, "isn't a date"),
        ({"type": "yes_no", "default": "yes"}, "true or false"),
    ],
)
def test_an_input_that_doesnt_hold_together_is_refused(spec: dict[str, Any], problem: str) -> None:
    with pytest.raises(ValidationError, match=problem):
        _inputs({"name": "x", **spec})


# -- conditions


@pytest.mark.parametrize(
    ("condition", "held"),
    [
        (_cond("Q1 report", "starts_with", "Q1"), True),
        (_cond("report.pdf", "ends_with", ".xlsx"), False),
        (_cond("overdue invoice", "not_contains", "paid"), True),
        (_cond([], "empty"), True),
        (_cond("2026-03-31", "before", "2026-04-01"), True),
        (_cond("2026-04-01T09:00", "after", "2026-04-01"), True),
        (_cond("2026-03-31", "after", "2026-04-01"), False),
    ],
)
def test_the_new_comparisons(condition: Condition, held: bool) -> None:
    assert conditions_hold([condition], "all", {})[0] is held


def test_a_date_that_isnt_one_is_an_error_not_a_guess() -> None:
    with pytest.raises(ValueError, match="as a date"):
        conditions_hold([_cond("last Friday", "before", "2026-04-01")], "all", {})


def test_any_holds_on_one_and_stops_there_so_a_later_condition_may_read_what_it_ruled_out() -> None:
    rows: list[Any] = []
    first_is_late = Condition.model_validate(
        {"left": {"ref": "rows.0.late"}, "op": "eq", "right": {"value": True}}
    )

    held, checked = conditions_hold([_cond(rows, "empty"), first_is_late], "any", {"rows": rows})

    assert held is True and len(checked) == 1
    assert conditions_hold([_cond(1, "eq", 2), _cond(1, "eq", 1)], "any", {})[0] is True
    assert conditions_hold([_cond(1, "eq", 2), _cond(1, "eq", 3)], "any", {})[0] is False
    assert conditions_hold([_cond(1, "eq", 1), _cond(1, "eq", 3)], "all", {})[0] is False


# -- the shape saved before decision 0031


def test_a_branch_and_an_approval_saved_with_one_condition_load_as_a_list() -> None:
    condition = {"left": {"ref": "n"}, "op": "gt", "right": {"value": 3}}
    saved = {
        "inputs": [{"name": "n", "type": "number"}],
        "steps": [
            {"id": "b", "kind": "branch", "title": "B", "condition": condition,
             "then": [_tool("t", "x")], "otherwise": []},
            {"id": "a", "kind": "approval", "title": "A", "message": "OK?", "when": condition},
            {"id": "a2", "kind": "approval", "title": "A2", "message": "OK?", "when": None},
        ],
    }  # fmt: skip

    now = current_shape(saved)

    assert now is not None
    assert [s.get("conditions") or s.get("when") for s in now["steps"][:2]] == [[condition]] * 2
    assert now["steps"][2]["when"] == []
    assert "condition" not in now["steps"][0]
    assert current_shape({"steps": "not a list"}) == {"steps": "not a list"}


# -- choice


def test_a_choice_takes_the_first_path_its_value_equals_ignoring_case() -> None:
    step = parse_workflow(_with_choice()).steps[0]

    assert choose_arm(step, {"dept": " finance"})[0] == "case:1"
    assert choose_arm(step, {"dept": "Ops"}) == (
        "otherwise",
        [(False, "Ops", ["Sales", "Finance"])],
    )


def test_a_name_every_path_of_a_choice_makes_is_read_after_it() -> None:
    after = {"id": "save", "kind": "tool", "title": "Save", "tool": "write_file",
             "args": {"path": "out.txt", "content": "{{text}}"}}  # fmt: skip
    parse_workflow(_with_choice(after))

    with pytest.raises(ValidationError, match="only one arm"):
        parse_workflow(_with_choice(after, otherwise=[_tool("other", "other_text")]))


def test_a_choice_needs_different_values_and_a_name_to_go_by() -> None:
    twice = [{"is": "Sales", "steps": []}, {"is": " sales", "steps": []}]
    with pytest.raises(ValidationError, match="different value"):
        parse_workflow(_with_choice(cases=twice))
    with pytest.raises(ValidationError, match="isn't a name"):
        parse_workflow(_with_choice(value="{{dept}}"))


def test_a_problem_inside_a_choice_path_names_its_step_number() -> None:
    data = _with_choice(otherwise=[{**_tool("other", "text"), "title": ""}])
    with pytest.raises(ValidationError) as caught:
        parse_workflow(data)

    assert [p.number for p in walk(parse_workflow(_with_choice()).steps)] == [1, 2, 3, 4]
    assert workflow_error(caught.value, data).startswith("step 4: title:")


async def test_a_choice_runs_the_path_for_its_value(tmp_path: Path) -> None:
    after = {"id": "save", "kind": "tool", "title": "Save", "tool": "write_file",
             "args": {"path": "out.txt", "content": "{{text}}"}}  # fmt: skip
    workflow = parse_workflow(_with_choice(after))
    h, files = _files_harness(tmp_path)

    finance = await h.run(InMemorySaver(), workflow, "t1").start({"dept": "Finance"})
    ops = await h.run(InMemorySaver(), workflow, "t2").start({"dept": "Ops"})

    assert finance.status == ops.status == "completed"
    assert files.reads == ["finance.txt", "other.txt"]
    assert [c[1]["content"] for c in h.calls] == ["text of finance.txt", "text of other.txt"]
    picked = [r.output for r in h.records if r.step_id == "pick" and r.status == "done"]
    assert picked == [{"arm": "case:1"}, {"arm": "otherwise"}]


# -- branch, check and approval with several conditions


async def test_a_branch_on_any_condition_and_an_approval_only_when_they_hold(
    tmp_path: Path,
) -> None:
    many = {"left": {"count": "files"}, "op": "gt", "right": {"value": 10}}
    has_b = {"left": {"ref": "files.1.path"}, "op": "eq", "right": {"value": "b.txt"}}
    workflow = parse_workflow({
        "steps": [
            {"id": "ls", "kind": "tool", "title": "List", "tool": "list_files", "args": {},
             "save_as": "files"},
            {"id": "big", "kind": "branch", "title": "Big?", "conditions": [many, has_b],
             "match": "any", "then": [_tool("yes", "text", "yes.txt")],
             "otherwise": [_tool("no", "text", "no.txt")]},
            {"id": "ok", "kind": "approval", "title": "OK?", "message": "Go on?",
             "when": [many], "match": "all"},
        ]
    })  # fmt: skip
    h, files = _files_harness(tmp_path)

    outcome = await h.run(InMemorySaver(), workflow).start({})

    assert outcome.status == "completed"
    assert files.reads == ["yes.txt"]
    assert [r.status for r in h.records if r.step_id == "ok"] == ["skipped"]


async def test_a_check_on_any_condition_fails_only_when_none_holds(tmp_path: Path) -> None:
    def check(*rights: int) -> Any:
        conditions = [{"left": {"value": 1}, "op": "eq", "right": {"value": r}} for r in rights]
        step = {"id": "c", "kind": "check", "title": "C", "conditions": conditions, "match": "any"}
        return parse_workflow({"steps": [step]})

    h = Harness(tmp_path, [])
    passed = await h.run(InMemorySaver(), check(2, 1), "t1").start({})
    failed = await h.run(InMemorySaver(), check(2, 3), "t2").start({})

    assert passed.status == "completed"
    assert failed.status == "failed" and failed.error == "none of the checks held"


# -- a loop that stops early


async def test_a_loop_stops_after_the_pass_its_until_holds_and_keeps_what_it_collected(
    tmp_path: Path,
) -> None:
    found = {"left": {"ref": "text"}, "op": "contains", "right": {"value": "b.txt"}}
    workflow = parse_workflow({
        "steps": [
            {"id": "ls", "kind": "tool", "title": "List", "tool": "list_files", "args": {},
             "save_as": "files"},
            {"id": "each", "kind": "loop", "title": "Each", "over": "files", "item": "file",
             "collect": "text", "save_as": "texts", "until": [found],
             "steps": [{**_tool("read", "text"), "args": {"path": "{{file.path}}"}}]},
        ]
    })  # fmt: skip
    h, files = _files_harness(tmp_path)

    outcome = await h.run(InMemorySaver(), workflow).start({})

    assert outcome.status == "completed"
    assert files.reads == ["a.txt", "b.txt"]
    assert outcome.values["texts"] == ["text of a.txt", "text of b.txt"]
    done = [r for r in h.records if r.step_id == "each" and r.status == "done"][-1]
    assert done.output["stopped_early"] is True and done.output["done"] == 2


def test_a_loops_until_reads_only_what_exists_after_a_pass() -> None:
    unknown = {"left": {"ref": "later"}, "op": "not_empty"}
    with pytest.raises(ValidationError, match="stops early by 'later'"):
        parse_workflow({
            "inputs": [{"name": "files", "type": "text"}],
            "steps": [{"id": "each", "kind": "loop", "title": "Each", "over": "files",
                       "steps": [_tool("read", "text")], "until": [unknown]}],
        })  # fmt: skip
