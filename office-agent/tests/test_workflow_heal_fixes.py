"""The revision a run's heals propose (decision 0030): the saved arguments a heal named, kept
only while the task still holds what the heal replaced; every other heal is left for a revision
drafted in a conversation."""

from typing import Any

from coscribe.workflows import heal_fixes

LABEL = 'textbox "Company name"'
NEW = 'textbox "Legal name"'


def _workflow() -> dict[str, Any]:
    name = {"id": "name", "kind": "tool", "title": "Enter Company name", "tool": "browser_type",
            "args": {"ref": LABEL, "text": "{{row}}"}}  # fmt: skip
    submit = {"id": "submit", "kind": "tool", "title": "Click Submit", "tool": "browser_click",
              "args": {"ref": 'button "Submit"'}, "irreversible": True}  # fmt: skip
    loop = {"id": "each", "kind": "loop", "title": "Each row", "over": "rows", "item": "row",
            "steps": [name, submit]}  # fmt: skip
    return {"inputs": [], "steps": [loop]}


def _healed(step_id: str, args: dict[str, str], was: dict[str, str], **more: Any) -> dict[str, Any]:
    return {"step_id": step_id, "title": step_id, "iteration": [0], "error": "gone",
            "did": f"healed {step_id}", "args": args, "was": was, **more}  # fmt: skip


def test_a_heal_that_named_its_change_is_a_fix_to_the_saved_step() -> None:
    saved = _workflow()
    healed = [
        _healed("name", {"ref": NEW}, {"ref": LABEL}),
        # The second row reused it: the same fix, not a second one.
        _healed("name", {"ref": NEW}, {"ref": LABEL}, carried=True, iteration=[1]),
    ]

    result = heal_fixes(saved, healed)

    assert result["fixes"] == [
        {"step_id": "name", "title": "name", "name": "ref", "was": LABEL, "now": NEW}
    ]
    assert result["workflow"]["steps"][0]["steps"][0]["args"] == {"ref": NEW, "text": "{{row}}"}
    assert result["left"] == []
    # The task as saved is untouched until the person saves the revision.
    assert saved["steps"][0]["steps"][0]["args"]["ref"] == LABEL


def test_a_fix_isnt_offered_once_the_task_changed_since_the_run() -> None:
    saved = _workflow()
    saved["steps"][0]["steps"][0]["args"]["ref"] = 'textbox "Business name"'

    result = heal_fixes(saved, [_healed("name", {"ref": NEW}, {"ref": LABEL})])

    assert (result["fixes"], result["workflow"]) == ([], None)


def test_a_heal_that_did_more_than_change_an_argument_is_left_for_a_revision() -> None:
    result = heal_fixes(_workflow(), [_healed("submit", {}, {})])

    assert result["fixes"] == []
    assert result["left"] == [{"step_id": "submit", "title": "submit", "did": "healed submit"}]


def test_a_step_healed_differently_on_different_items_is_left_for_a_revision() -> None:
    healed = [
        _healed("name", {"ref": NEW}, {"ref": LABEL}),
        _healed("name", {"ref": 'textbox "Trading name"'}, {"ref": LABEL}, iteration=[1]),
    ]

    result = heal_fixes(_workflow(), healed)

    assert result["fixes"] == []
    assert [item["step_id"] for item in result["left"]] == ["name"]


def test_a_heal_from_before_the_replaced_values_were_kept_offers_nothing() -> None:
    result = heal_fixes(_workflow(), [_healed("name", {"ref": NEW}, {})])

    assert result == {"fixes": [], "workflow": None, "left": []}
