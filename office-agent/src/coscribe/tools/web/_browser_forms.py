"""Filling a page and acting on it several times in one step, and waiting for the first of
several outcomes: what a saved workflow does to a form without a step per field."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ._browser_pages import DEFAULT_TIMEOUT, DEFAULT_WAIT, wait_limit, with_tab

# What each action of browser_steps may carry besides its target.
_STEP_EXTRAS = {
    "click": set(),
    "type": {"text", "submit"},
    "select": {"values"},
    "press_key": set(),
    "wait_for": set(),
    "fill": set(),
}


def _check_fields(fields: Any) -> list[dict[str, str]]:
    if (
        not isinstance(fields, list)
        or not fields
        or any(not isinstance(f, dict) or set(f) != {"ref", "text"} for f in fields)
    ):
        raise ValueError("Provide fields with ref and text.")
    return fields


def _check_steps(steps: Any) -> int:
    """How many fields and actions the steps hold, each of which may wait for its element."""
    if not isinstance(steps, list) or not steps:
        raise ValueError("Provide the steps to do, in order.")
    waits = 0
    for number, step in enumerate(steps, 1):
        actions = [k for k in step if k in _STEP_EXTRAS] if isinstance(step, dict) else []
        if len(actions) != 1:
            raise ValueError(f"Step {number} must name exactly one of {', '.join(_STEP_EXTRAS)}.")
        extra = set(step) - {actions[0]} - _STEP_EXTRAS[actions[0]]
        if extra:
            raise ValueError(f"Step {number} ({actions[0]}) takes no {', '.join(sorted(extra))}.")
        waits += len(_check_fields(step["fill"])) if actions[0] == "fill" else 1
    return waits


def _changed_lines(filled: Any) -> list[str]:
    return [
        f'{field.get("element")} now holds "{field.get("value")}" -- the page changed what was '
        "given; check it."
        for field in filled or []
        if isinstance(field, dict) and field.get("changed")
    ]


def form_tools(call: Callable[..., dict[str, Any]]) -> dict[str, Callable[..., Any]]:
    def browser_fill_form(
        fields: list[dict[str, str]], tab_id: int | str = 0, timeout: float = DEFAULT_WAIT
    ) -> str:
        """Fill named fields in order, each the way a person would: text is typed, a
        dropdown chooses the option, a checkbox takes "checked" or "unchecked", a radio
        button is chosen, a date or time field takes its fixed format (2026-11-16, 14:30).
        Each field is read back; the result names any the page changed.

        Args:
            fields: objects with ref (snapshot ref or field description) and text
            timeout: seconds to wait for each field
            tab_id: runtime tab id or saved name; 0 uses the selected automation page
        """
        _check_fields(fields)
        wait = wait_limit(timeout)
        result = call(
            "fill_form", wait * len(fields) + DEFAULT_TIMEOUT, fields=fields, tab_id=tab_id,
            timeout=wait,
        )  # fmt: skip
        lines = [f"Filled {len(fields)} field{'s' if len(fields) != 1 else ''}."]
        return with_tab("\n".join(lines + _changed_lines(result.get("filled"))), result)

    def browser_steps(
        steps: list[dict[str, Any]], tab_id: int | str = 0, timeout: float = DEFAULT_WAIT
    ) -> str:
        """Do several things on one page in one step, in order, stopping at the first
        that fails (the error says which, and what was done before it). Each step names
        one action: {"fill": [{"ref", "text"}, ...]}, {"type": ref, "text": ..., "submit":
        true}, {"select": ref, "values": [...]}, {"click": ref}, {"press_key": "Enter"},
        {"wait_for": text}. Refs are as for the single-action tools.

        Args:
            steps: the actions, in order
            timeout: seconds each action may wait for its element or text
            tab_id: runtime tab id or saved name; 0 uses the selected automation page
        """
        waits = _check_steps(steps)
        wait = wait_limit(timeout)
        result = call("steps", wait * waits + DEFAULT_TIMEOUT, steps=steps, tab_id=tab_id,
                      timeout=wait)  # fmt: skip
        done = result.get("done") or []
        return with_tab(f"Did {len(done)} step{'s' if len(done) != 1 else ''}.", result)

    return {"browser_fill_form": browser_fill_form, "browser_steps": browser_steps}


def wait_for_any(
    call: Callable[..., dict[str, Any]],
    texts: list[str],
    others: list[Any],
    timeout: float,
    tab_id: int | str,
) -> dict[str, Any]:
    """browser_wait_for(any_of=...): a value a saved workflow's next step can branch on."""
    if any(others):
        raise ValueError("Wait for one thing at a time: any_of goes alone.")
    if not texts or any(not isinstance(t, str) or not t for t in texts):
        raise ValueError("any_of lists the texts to wait for.")
    limit = wait_limit(timeout)
    result = call("wait_for", limit + 15, any_of=texts, timeout=limit, tab_id=tab_id)
    found = str(result.get("found_text") or "")
    return {"found": found, "message": with_tab(f'"{found}" is on the page.', result)}
