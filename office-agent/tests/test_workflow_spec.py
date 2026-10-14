import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from coscribe.workflows.refs import (
    UnresolvedReference,
    evaluate,
    render_text,
    render_value,
    resolve,
)
from coscribe.workflows.spec import (
    BranchStep,
    Condition,
    LoopStep,
    Operand,
    _locate,
    child_lists,
    parse_workflow,
    walk,
    workflow_error,
)

FIXTURE = Path(__file__).parent / "fixtures" / "pdf_error_audit_workflow.json"


def _audit() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_the_pdf_audit_workflow_parses() -> None:
    workflow = parse_workflow(_audit())

    assert [s.kind for s in workflow.steps] == [
        "tool", "tool", "check", "script", "llm", "check", "approval", "tool",
    ]  # fmt: skip
    assert workflow.inputs[0].default == "big_manual.pdf"


def test_a_reference_to_a_later_step_is_rejected_at_save_time() -> None:
    data = _audit()
    data["steps"][0], data["steps"][4] = data["steps"][4], data["steps"][0]

    with pytest.raises(ValidationError, match=r"reads 'page_count.pages', which isn't an input"):
        parse_workflow(data)


def test_a_typo_in_a_reference_is_rejected() -> None:
    data = _audit()
    data["steps"][5]["conditions"][0]["left"] = {"ref": "sumary.error_count"}

    with pytest.raises(ValidationError, match="sumary.error_count"):
        parse_workflow(data)


@pytest.mark.parametrize(
    ("step", "field", "text"),
    [
        (4, "prompt", "There are {{count:matches}} lines."),
        (6, "message", "Check {{ summary.summary | upper }} first."),
    ],
)
def test_an_expression_in_braces_is_rejected_not_left_as_text(
    step: int, field: str, text: str
) -> None:
    data = _audit()
    data["steps"][step][field] = text

    with pytest.raises(ValidationError, match=r"isn't a reference -- write \{\{name\}\}"):
        parse_workflow(data)


def test_braces_in_tool_arguments_are_checked_too() -> None:
    data = _audit()
    data["steps"][7]["args"]["content"] = "Pages: {{page_count.pages + 1}}"

    with pytest.raises(ValidationError, match=r"step 8 \('Write the report'\)"):
        parse_workflow(data)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["steps"][1].update(id="search"), "id 'search' is used twice"),
        (lambda d: d["steps"][1].update(save_as="matches"), "'matches' is already taken"),
        (lambda d: d["steps"][1].update(save_as="pdf_path"), "'pdf_path' is already taken"),
        (lambda d: d["steps"][0].update(id="Search Step"), "must start with a lowercase letter"),
        (lambda d: d["steps"][4].update(fields=[]), "at least 1 item"),
        (lambda d: d["steps"][4].pop("save_as"), "save_as"),
        (lambda d: d["steps"][0].update(kind="agent"), "tag 'agent'"),
        (lambda d: d["steps"][0].update(surprise=1), "surprise"),
    ],
)
def test_malformed_workflows_are_rejected(mutate: Any, message: str) -> None:
    data = _audit()
    mutate(data)

    with pytest.raises(ValidationError, match=message):
        parse_workflow(data)


def test_an_operand_is_exactly_one_thing() -> None:
    with pytest.raises(ValidationError, match="exactly one of"):
        Condition.model_validate(
            {"left": {"ref": "a", "value": 1}, "op": "eq", "right": {"value": 1}}
        )
    with pytest.raises(ValidationError, match="not_empty takes no right-hand side"):
        Condition.model_validate({"left": {"ref": "a"}, "op": "not_empty", "right": {"value": 1}})
    with pytest.raises(ValidationError, match="needs one"):
        Condition.model_validate({"left": {"ref": "a"}, "op": "eq"})


VALUES = {
    "pdf_path": "big.pdf",
    "matches": [{"page": 97, "text": "Error code E-0097"}, {"page": 194, "text": "x"}],
    "summary": {"error_count": 2, "accounts": ["4410-97"], "boilerplate": True},
}


def test_resolve_walks_dicts_and_list_indexes() -> None:
    assert resolve("matches.1.page", VALUES) == 194
    assert resolve("summary.accounts", VALUES) == ["4410-97"]
    with pytest.raises(UnresolvedReference, match="'summary' has no 'total'"):
        resolve("summary.total", VALUES)
    with pytest.raises(UnresolvedReference, match="'later' has no value yet"):
        resolve("later", VALUES)


def test_a_whole_reference_keeps_its_type_and_embedded_ones_become_text() -> None:
    assert render_value("{{summary.accounts}}", VALUES) == ["4410-97"]
    assert render_value({"path": "{{pdf_path}}", "n": 3}, VALUES) == {"path": "big.pdf", "n": 3}
    assert (
        render_text("File {{pdf_path}}, {{summary.error_count}} errors", VALUES)
        == "File big.pdf, 2 errors"
    )
    assert '"page": 97' in render_text("{{matches}}", VALUES)
    assert render_text("Accounts: {{summary.accounts}}", {"summary": {"accounts": ["a", "b"]}}) == (
        "Accounts: a, b"
    )


def _condition(left: dict[str, Any], op: str, right: dict[str, Any] | None = None) -> Condition:
    return Condition.model_validate(
        {"left": left, "op": op, "right": right} if right else {"left": left, "op": op}
    )


def test_evaluate_reports_what_it_compared() -> None:
    assert evaluate(
        _condition({"count": "matches"}, "eq", {"ref": "summary.error_count"}), VALUES
    ) == (True, 2, 2)
    assert evaluate(
        _condition({"count": "summary.accounts"}, "eq", {"ref": "summary.error_count"}), VALUES
    ) == (
        False,
        1,
        2,
    )
    assert (
        evaluate(_condition({"ref": "summary.error_count"}, "eq", {"value": "2"}), VALUES)[0]
        is True
    )
    assert (
        evaluate(_condition({"ref": "summary.error_count"}, "gt", {"value": 1}), VALUES)[0] is True
    )
    assert (
        evaluate(_condition({"ref": "summary.accounts"}, "contains", {"value": "4410-97"}), VALUES)[
            0
        ]
        is True
    )
    assert (
        evaluate(_condition({"ref": "summary.boilerplate"}, "eq", {"value": False}), VALUES)[0]
        is False
    )
    assert evaluate(_condition({"ref": "summary.accounts"}, "not_empty"), VALUES)[0] is True


def test_evaluate_refuses_nonsense_comparisons() -> None:
    with pytest.raises(UnresolvedReference, match="as numbers"):
        evaluate(_condition({"ref": "pdf_path"}, "gt", {"value": 1}), VALUES)
    with pytest.raises(UnresolvedReference, match="can't count"):
        evaluate(_condition({"count": "summary.error_count"}, "eq", {"value": 1}), VALUES)


def test_a_saved_workflow_loads_back_unchanged() -> None:
    workflow = parse_workflow(_audit())
    saved = workflow.model_dump(mode="json")

    assert parse_workflow(saved) == workflow
    assert saved["steps"][2]["conditions"][0]["left"] == {"count": "matches"}
    assert saved["steps"][6]["when"]["right"] == {"value": False}


def _tool(step_id: str, save_as: str | None = None, **args: Any) -> dict[str, Any]:
    return {
        "id": step_id, "kind": "tool", "title": step_id.title(), "tool": "read_file",
        "args": args, "save_as": save_as,
    }  # fmt: skip


def _branch(then: list[Any], otherwise: list[Any]) -> dict[str, Any]:
    return {
        "id": "decide", "kind": "branch", "title": "Decide",
        "condition": {"left": {"count": "files"}, "op": "gt", "right": {"value": 0}},
        "then": then, "otherwise": otherwise,
    }  # fmt: skip


def _loop(body: list[Any], **extra: Any) -> dict[str, Any]:
    return {
        "id": "each", "kind": "loop", "title": "Each file", "over": "files",
        "item": "file", "steps": body, **extra,
    }  # fmt: skip


def _with(*steps: Any) -> dict[str, Any]:
    return {"inputs": [{"name": "files", "default": "a"}], "steps": list(steps)}


def test_a_value_both_arms_produce_is_readable_after_the_branch() -> None:
    workflow = parse_workflow(
        _with(
            _branch([_tool("a", "text", path="x")], [_tool("b", "text", path="y")]),
            _tool("after", path="{{text}}"),
        )
    )
    assert [p.number for p in walk(workflow.steps)] == [1, 2, 3, 4]
    assert [p.step.id for p in walk(workflow.steps)] == ["decide", "a", "b", "after"]


def test_a_value_only_one_arm_produces_is_not() -> None:
    data = _with(
        _branch([_tool("a", "text", path="x")], [_tool("b", path="y")]),
        _tool("after", path="{{text}}"),
    )
    with pytest.raises(
        ValidationError, match=r"step 4 \('After'\) reads 'text'.*only one arm of a branch"
    ):
        parse_workflow(data)


def test_a_loop_body_sees_its_item_and_only_the_collected_list_leaks() -> None:
    body = [_tool("read", "text", path="{{file.path}}")]
    workflow = parse_workflow(
        _with(
            _loop(body, collect="text", save_as="texts"),
            _tool("after", path="{{texts}}"),
            # Its names are free again after the loop.
            {**_loop([_tool("again", "text", path="{{file}}")]), "id": "each2"},
        )
    )
    placed = walk(workflow.steps)
    assert [(p.number, p.step.id, p.loops) for p in placed] == [
        (1, "each", ()), (2, "read", ("each",)), (3, "after", ()), (4, "each2", ()),
        (5, "again", ("each2",)),
    ]  # fmt: skip

    leaky = _with(_loop(body), _tool("after", path="{{text}}"))
    with pytest.raises(ValidationError, match="made inside a loop"):
        parse_workflow(leaky)


@pytest.mark.parametrize(
    ("loop", "message"),
    [
        (_loop([_tool("read", "text", path="{{file}}")], collect="texts"), "go together"),
        (
            _loop([_tool("read", "text", path="x")], collect="files", save_as="t"),
            "collects 'files'",
        ),
        (_loop([], over="files | first"), "isn't a name like"),
        (_loop([], item="files"), "'files' is already taken"),
        (_loop([], max_items=500), "less than or equal to 200"),
    ],
)
def test_malformed_loops_are_rejected(loop: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        parse_workflow(_with(loop))


def test_blocks_nest_three_deep_at_most() -> None:
    inner: dict[str, Any] = _tool("leaf", path="x")
    for depth in range(4):
        inner = {**_branch([inner], []), "id": f"b{depth}"}
    with pytest.raises(ValidationError, match="nest at most 3 deep"):
        parse_workflow(_with(inner))


def test_errors_inside_blocks_are_numbered_like_the_editor() -> None:
    data = _with(
        _tool("first", path="x"),
        _branch([_tool("a", path="x")], [_tool("b", path="y"), {"id": "bad", "kind": "tool"}]),
    )
    with pytest.raises(ValidationError) as caught:
        parse_workflow(data)
    assert workflow_error(caught.value, data).startswith("step 5: title: Field required")


def test_a_model_steps_fields_are_the_only_ones_to_read() -> None:
    data = _audit()
    data["steps"][5]["conditions"][0]["left"] = {"ref": "summary.errors"}
    with pytest.raises(
        ValidationError,
        match=r"reads 'summary.errors', but summary only has "
        r"accounts, boilerplate, error_count, summary",
    ):
        parse_workflow(data)

    loop = _loop(
        [{"id": "sum", "kind": "llm", "title": "Sum", "prompt": "{{file}}",
          "fields": [{"name": "summary"}], "save_as": "note"}],
        collect="note.text", save_as="notes",
    )  # fmt: skip
    with pytest.raises(ValidationError, match="reads 'note.text', but note only has summary"):
        parse_workflow(_with(loop))


# -- what a save-time error says, word for word --


def _error(data: Any) -> str:
    with pytest.raises(ValidationError) as caught:
        parse_workflow(data)
    return workflow_error(caught.value, data)


def _llm(step_id: str, save_as: str, *fields: str) -> dict[str, Any]:
    return {
        "id": step_id, "kind": "llm", "title": step_id.title(), "prompt": "go",
        "fields": [{"name": f} for f in fields], "save_as": save_as,
    }  # fmt: skip


def _script(step_id: str, **inputs: Any) -> dict[str, Any]:
    return {
        "id": step_id, "kind": "script", "title": step_id.title(), "code": "print(1)",
        "inputs": inputs,
    }  # fmt: skip


def _check(*conditions: dict[str, Any]) -> dict[str, Any]:
    return {"id": "gate", "kind": "check", "title": "Gate", "conditions": list(conditions)}


def _approval(when: dict[str, Any] | None = None, message: str = "ok?") -> dict[str, Any]:
    step: dict[str, Any] = {"id": "ask", "kind": "approval", "title": "Ask", "message": message}
    if when is not None:
        step["when"] = when
    return step


def test_a_bad_name_says_what_a_name_looks_like() -> None:
    assert _error({"inputs": [{"name": "Bad"}]}) == (
        "inputs.0.name: 'Bad' must start with a lowercase letter and use only a-z, 0-9 and _ "
        "(at most 40 characters)"
    )
    parse_workflow({"inputs": [{"name": "a" + "b" * 39}]})
    assert "at most 40" in _error({"inputs": [{"name": "a" + "b" * 40}]})


def test_a_problem_outside_the_steps_has_no_step_number() -> None:
    assert _error({"inputs": [{"name": "a"}, {"name": "a"}]}) == "input names must be unique"


def test_several_problems_are_joined_with_semicolons() -> None:
    data = {"steps": [{"id": "x", "kind": "tool"}]}

    assert _error(data) == "step 1: title: Field required; step 1: tool: Field required"


def test_an_operand_is_read_by_its_reference_or_count_and_a_value_has_none() -> None:
    assert Operand(ref="a.b").reference() == "a.b"
    assert Operand(count="files").reference() == "files"
    assert Operand(value=3).reference() is None


def test_a_deep_reference_is_judged_by_its_first_name() -> None:
    parse_workflow(_with(_tool("a", path="{{files.x.y.z}}")))


def test_both_sides_of_a_condition_must_name_something_that_exists() -> None:
    ghost_left = _check({"left": {"ref": "ghost"}, "op": "eq", "right": {"value": 1}})
    ghost_right = _check({"left": {"ref": "files"}, "op": "eq", "right": {"ref": "ghost"}})

    assert _error(_with(ghost_left)) == (
        "step 1 ('Gate') reads 'ghost', which isn't an input or the result of an earlier step"
    )
    assert _error(_with(ghost_right)) == (
        "step 1 ('Gate') reads 'ghost', which isn't an input or the result of an earlier step"
    )
    parse_workflow(_with(_check({"left": {"ref": "files"}, "op": "not_empty"})))
    parse_workflow(
        _with(_branch([], []) | {"condition": {"left": {"ref": "files"}, "op": "not_empty"}})
    )


def test_an_approval_condition_is_checked_only_when_there_is_one() -> None:
    parse_workflow(_with(_approval()))
    parse_workflow(_with(_approval({"left": {"ref": "files"}, "op": "not_empty"})))

    assert "reads 'ghost'" in _error(
        _with(_approval({"left": {"ref": "ghost"}, "op": "not_empty"}))
    )


def test_references_inside_lists_and_script_inputs_are_checked() -> None:
    missing = "reads 'ghost', which isn't an input or the result of an earlier step"

    assert missing in _error(_with(_tool("a", paths=["{{files}}", ["{{ghost}}"]])))
    assert missing in _error(_with(_script("s", nested={"deep": ["{{ghost}}"]})))
    parse_workflow(_with(_script("s", nested={"deep": ["{{files}}"]})))


def test_a_template_that_is_not_a_reference_is_refused_wherever_it_hides() -> None:
    for step in (
        _tool("a", paths=["x", ["{{files | upper}}"]]),
        _script("s", nested={"deep": ["{{files | upper}}"]}),
    ):
        assert "isn't a reference -- write {{name}} or {{name.field}}" in _error(_with(step))


def test_a_blocks_lists_are_named_in_document_order() -> None:
    branch = parse_workflow(_with(_branch([_tool("a", path="x")], [_tool("b", path="y")])))
    loop = parse_workflow(_with(_loop([_tool("c", path="{{file}}")])))

    (branch_step,) = branch.steps
    (loop_step,) = loop.steps
    assert isinstance(branch_step, BranchStep) and isinstance(loop_step, LoopStep)
    assert child_lists(branch_step) == [
        ("then", branch_step.then),
        ("otherwise", branch_step.otherwise),
    ]
    assert child_lists(loop_step) == [("steps", loop_step.steps)]
    assert child_lists(branch_step.then[0]) == []


def test_only_a_loop_adds_itself_to_the_loops_around_its_steps() -> None:
    workflow = parse_workflow(
        _with(
            _branch([_tool("a", path="x")], []),
            {
                **_loop([_branch([_tool("c", path="{{file}}")], []) | {"id": "inner"}]),
                "id": "outer",
            },
        )
    )

    assert [(p.step.id, p.loops) for p in walk(workflow.steps)] == [
        ("decide", ()), ("a", ()), ("outer", ()), ("inner", ("outer",)), ("c", ("outer",)),
    ]  # fmt: skip


def test_a_field_is_judged_by_its_first_name_after_the_result() -> None:
    steps = [_llm("m", "note", "summary")]

    parse_workflow(_with(*steps, _tool("a", path="{{note.summary.deep.er}}")))
    parse_workflow(_with(*steps, _tool("a", path="{{note.summary}}")))
    assert _error(_with(*steps, _tool("a", path="{{note.nope.deeper}}"))) == (
        "step 2 ('A') reads 'note.nope.deeper', but note only has summary"
    )


def test_what_a_step_cannot_read_is_explained_and_a_loop_or_arm_name_is_hinted() -> None:
    assert _error(_with(_tool("a", path="{{ghost}}"))) == (
        "step 1 ('A') reads 'ghost', which isn't an input or the result of an earlier step"
    )
    hint = " here (it's made inside a loop, or in only one arm of a branch)"
    one_arm = _branch([_tool("a", "x", path="1")], [])
    other_arm = {**_branch([], [_tool("b", "y", path="2")]), "id": "decide2"}
    assert _error(_with(one_arm, other_arm, _tool("z", path="{{x}}"))) == (
        "step 5 ('Z') reads 'x', which isn't an input or the result of an earlier step" + hint
    )
    in_loop = _loop([_tool("c", "inside", path="{{file}}")])
    assert _error(_with(in_loop, _tool("z", path="{{inside}}"))) == (
        "step 3 ('Z') reads 'inside', which isn't an input or the result of an earlier step" + hint
    )


def test_names_hinted_from_two_loops_are_both_remembered() -> None:
    hint = " here (it's made inside a loop, or in only one arm of a branch)"
    first = _loop([_tool("c", "one", path="{{file}}")])
    second = {**_loop([_tool("d", "two", path="{{file}}")]), "id": "each2"}

    message = _error(_with(first, second, _tool("z", path="{{one}}")))

    assert message.endswith(hint)


def test_a_workflow_has_at_most_a_hundred_steps_nested_ones_included() -> None:
    flat = [_tool(f"t{i}", path="x") for i in range(98)]
    fits = _branch([_tool("in1", path="x")], [])
    too_many = _branch([_tool("in1", path="x"), _tool("in2", path="x")], [])

    parse_workflow(_with(*flat, fits))
    assert (
        _error(_with(*flat, too_many)) == "a workflow has at most 100 steps, nested ones included"
    )


def test_a_step_id_and_a_saved_name_may_be_used_once() -> None:
    assert _error(_with(_tool("a", path="x"), _tool("a", path="y"))) == (
        "step 2: id 'a' is used twice"
    )
    assert _error(_with(_tool("a", "x", path="1"), _tool("b", "x", path="2"))) == (
        "step 2: 'x' is already taken"
    )


def test_what_a_branch_saves_stays_taken_after_it_whichever_arm_saved_it() -> None:
    then_only = _branch([_tool("a", "x", path="1")], [])
    otherwise_only = _branch([], [_tool("a", "x", path="1")])
    both = _branch([_tool("a", "x", path="1")], [_tool("b", "x", path="2")])

    for branch in (then_only, otherwise_only, both):
        assert _error(_with(branch, _tool("later", "x", path="3"))).endswith("'x' is already taken")


def test_a_branch_leaves_earlier_and_input_names_readable() -> None:
    parse_workflow(
        _with(
            _tool("first", "early", path="x"),
            _branch([_tool("a", "x", path="1")], [_tool("b", "x", path="2")]),
            _tool("after", path="{{early}} {{files}} {{x}}"),
        )
    )


def _nest(kind: str, arm: str, depth: int) -> dict[str, Any]:
    """`depth` blocks inside one another, each holding the next in `arm`."""
    inner: dict[str, Any] = _tool("leaf", path="x")
    for level in range(depth):
        if kind == "loop":
            block = {**_loop([inner]), "item": f"item{level}"}
        else:
            block = {**_branch([], []), arm: [inner]}
        inner = {**block, "id": f"b{level}"}
    return inner


@pytest.mark.parametrize("kind", ["loop", "then", "otherwise"])
def test_blocks_nest_three_deep_in_any_arm_but_not_four(kind: str) -> None:
    shape = "loop" if kind == "loop" else "branch"

    parse_workflow(_with(_nest(shape, kind, 3)))
    assert _error(_with(_nest(shape, kind, 4))).endswith("branches and loops nest at most 3 deep")


def test_a_loop_names_its_item_and_says_what_it_cannot_collect() -> None:
    assert _error(_with(_loop([_tool("a", "file", path="x")]))) == (
        "step 2: 'file' is already taken"
    )
    inner = {**_loop([_tool("a", path="x")]), "id": "inner", "over": "files"}
    assert _error(_with(_loop([inner]))) == (
        "step 2 ('Each file'): 'file' is already taken, name the item differently"
    )
    assert _error(_with(_loop([_tool("a", "t", path="x")], collect="files", save_as="ts"))) == (
        "step 1 ('Each file') collects 'files', which isn't the item or a result of "
        "a step inside the loop"
    )
    note = _loop([_llm("m", "note", "summary")], collect="note.text", save_as="notes")
    assert _error(_with(note)) == (
        "step 1 ('Each file') reads 'note.text', but note only has summary"
    )


# -- where an error is located --


def _step_data(kind: str, **extra: Any) -> dict[str, Any]:
    return {"id": kind, "kind": kind, "title": kind, **extra}


@pytest.mark.parametrize(
    ("loc", "expected"),
    [
        (["steps"], (None, ["steps"])),
        (["inputs", 0], (None, ["inputs", 0])),
        (["other", 0, "title"], (None, ["other", 0, "title"])),
        (["steps", "x"], (None, ["steps", "x"])),
        (["steps", 0], (1, [])),
        (["steps", 0, "title"], (1, ["title"])),
        (["steps", 0, "tool", "title"], (1, ["title"])),
        (["steps", 0, "tool", "args", "path"], (1, ["args", "path"])),
        (["steps", 9, "tool", "title"], (1, ["title"])),
    ],
)
def test_locating_an_error_in_flat_data(
    loc: list[Any], expected: tuple[int | None, list[Any]]
) -> None:
    assert _locate({"steps": []}, loc) == expected
    assert _locate(None, loc) == expected


def test_locating_counts_every_step_before_it_nested_ones_included() -> None:
    loop = _step_data("loop", steps=[_step_data("tool"), _step_data("tool")])
    branch = _step_data("branch", then=[_step_data("tool")], otherwise=[_step_data("tool"), {}])
    data = {"steps": ["junk", loop, branch, {}]}

    assert _locate(data, ["steps", 1, "loop", "title"]) == (2, ["title"])
    assert _locate(data, ["steps", 2, "branch", "title"])[0] == 5
    assert _locate(data, ["steps", 3, "tool", "title"]) == (9, ["title"])
    assert _locate(data, ["steps", 0, "tool", "title"])[0] == 1
    assert _locate(data, ["steps", 1, "loop", "steps", 1, "tool", "title"]) == (4, ["title"])
    assert _locate(data, ["steps", 2, "branch", "then", 0, "tool", "title"]) == (6, ["title"])
    assert _locate(data, ["steps", 2, "branch", "otherwise", 1, "tool", "title"]) == (8, ["title"])
    assert _locate(data, ["steps", 2, "branch", "then", 0]) == (6, [])


def test_locating_goes_two_levels_down() -> None:
    inner = _step_data("branch", then=[_step_data("tool")], otherwise=[_step_data("tool")])
    outer = _step_data("loop", steps=[_step_data("tool"), inner])
    data = {"steps": [outer]}

    loc = ["steps", 0, "loop", "steps", 1, "branch", "otherwise", 0, "tool", "title"]
    assert _locate(data, loc) == (5, ["title"])


def test_a_block_inside_a_block_counts_all_its_steps_when_numbering_what_follows() -> None:
    inner = _step_data("branch", then=[_step_data("tool"), _step_data("tool")])
    data = {"steps": [_step_data("loop", steps=[inner]), _step_data("tool")]}

    assert _locate(data, ["steps", 1, "tool", "title"]) == (5, ["title"])


def test_the_steps_of_a_nested_then_arm_are_counted_before_the_otherwise_arm() -> None:
    branch = _step_data(
        "branch",
        then=[_step_data("branch", then=[_step_data("tool")])],
        otherwise=[_step_data("tool")],
    )

    assert _locate(
        {"steps": [branch]}, ["steps", 0, "branch", "otherwise", 0, "tool", "title"]
    ) == (
        4,
        ["title"],
    )
