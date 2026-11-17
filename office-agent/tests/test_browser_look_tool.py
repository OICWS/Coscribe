"""Seeing the page as a picture, clicking by position, and reading the text by a label --
and a saved workflow that watches a page for a change."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from coscribe.runtime import get_tool_metadata
from coscribe.tools.web.browser import BrowserHost, build_browser_tools


class _Host(BrowserHost):
    def __init__(self, replies: dict[str, dict[str, Any]]) -> None:
        super().__init__()
        self.replies = replies
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(
        self, action: str, args: dict[str, Any], thread_id: str, timeout: float = 30
    ) -> dict[str, Any]:
        self.calls.append((action, args))
        return self.replies[action]


def _tools(host: BrowserHost, **kwargs: Any) -> dict[str, Any]:
    return {t.__name__: t for t in build_browser_tools("t1", host, **kwargs)}


def test_a_screenshot_is_a_picture_with_its_size() -> None:
    tab = {"id": 2, "title": "Map", "url": "https://map.example/"}
    host = _Host({"look": {"png": "iVBO", "width": 1280, "height": 720, "tab": tab}})
    text, picture = _tools(host)["browser_screenshot"]()
    assert text["text"].startswith(
        "Tab 2: Map -- https://map.example/\nThe page's visible part, 1280x720"
    )
    assert picture == {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBO"}}


def test_a_click_by_position_goes_in_the_pictures_pixels() -> None:
    host = _Host({"click_at": {}})
    tools = _tools(host)
    assert tools["browser_click_at"](40, 300, double=True).startswith(
        "Double-clicked at (40, 300)."
    )
    assert (host.calls[0][0], host.calls[0][1]["x"], host.calls[0][1]["y"]) == ("click_at", 40, 300)
    with pytest.raises(ValueError):
        tools["browser_click_at"](-1, 5)


def test_reading_by_a_label_gives_a_value_a_workflow_can_compare() -> None:
    host = _Host({"read_text": {"text": "Price ¥89"}})
    result = _tools(host)["browser_read_text"]("Price", timeout=5)
    assert result["text"] == "Price ¥89"
    assert host.calls[0][1]["near"] == "Price" and host.calls[0][1]["timeout"] == 5


def test_seeing_and_reading_are_read_only_and_clicking_acts() -> None:
    tools = _tools(_Host({}))
    risks = {name: get_tool_metadata(tools[name]).risk_category for name in tools}
    assert risks["browser_screenshot"] == risks["browser_read_text"] == "READ"
    assert risks["browser_click_at"] == "EXTERNAL"


async def test_a_task_that_watches_a_page_ends_quietly_until_it_changes(tmp_path: Path) -> None:
    pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")
    from langgraph.checkpoint.memory import InMemorySaver

    from coscribe.workflow_spec import parse_workflow
    from coscribe.workflows.engine import StepContext, WorkflowRun

    host = _Host({"navigate": {}, "read_text": {"text": "Price ¥89"}})
    ctx = StepContext(tools=_tools(host, saved_workflow=True), workspace_root=tmp_path,
                      state_dir=tmp_path / "state", make_model=lambda name: None)  # fmt: skip
    workflow = parse_workflow(
        {
            "memory": [{"name": "price", "label": "Price", "type": "text", "initial": ""}],
            "steps": [
                {"id": "open", "kind": "tool", "title": "Open", "tool": "browser_navigate",
                 "args": {"url": "https://shop.example/item"}},
                {"id": "read", "kind": "tool", "title": "Read the price",
                 "tool": "browser_read_text", "args": {"near": "Price"}, "save_as": "now"},
                {"id": "changed", "kind": "check", "title": "Changed?", "otherwise": "end",
                 "conditions": [{"left": {"ref": "now.text"}, "op": "ne",
                                 "right": {"ref": "memory.price"}}]},
                {"id": "keep", "kind": "remember", "title": "Keep it", "name": "price",
                 "value": "{{now.text}}"},
            ],
        }
    )  # fmt: skip

    def run(memory: dict[str, Any]) -> Any:
        return WorkflowRun(workflow, ctx, InMemorySaver(), "run-1", lambda record: None).start(
            {}, memory
        )

    first = await run({"price": ""})
    assert first.status == "completed" and first.remembered == {"price": "Price ¥89"}
    same = await run({"price": "Price ¥89"})
    assert same.status == "completed" and same.ended and not same.remembered
