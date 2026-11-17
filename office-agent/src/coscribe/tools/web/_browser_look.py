"""Seeing the page as a picture and clicking by position, for what has no element to name (a
canvas, a chart, an icon without a label), and reading the text by a label, for a value a
saved workflow compares with the last run's to tell the person what changed."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ._browser_pages import DEFAULT_TIMEOUT, DEFAULT_WAIT, tab_line, wait_limit, with_tab


def look_tools(call: Callable[..., dict[str, Any]]) -> dict[str, Callable[..., Any]]:
    def browser_screenshot(tab_id: int | str = 0) -> list[dict[str, Any]]:
        """See the visible part of the page as a picture. For what browser_snapshot
        doesn't name -- a canvas, a chart, a map, an icon without a label -- then click
        it with browser_click_at. Prefer the snapshot's refs wherever they exist.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        result = call("look", tab_id=tab_id)
        text = (
            f"The page's visible part, {result.get('width')}x{result.get('height')} pixels; "
            "browser_click_at takes x and y in this picture's pixels from its top left."
        )
        line = tab_line(result.get("tab"))
        picture = {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{result['png']}"},
        }
        return [{"type": "text", "text": f"{line}\n{text}" if line else text}, picture]

    def browser_click_at(x: int, y: int, double: bool = False, tab_id: int | str = 0) -> str:
        """Click a point of the page as the last browser_screenshot showed it, for what has
        no ref. Take a new screenshot after the page changes, scrolls or resizes.

        Args:
            x: pixels from the picture's left edge
            y: pixels from the picture's top edge
            double: a double click
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        if x < 0 or y < 0:
            raise ValueError("x and y are pixels from the picture's top left, 0 or more.")
        result = call("click_at", x=x, y=y, double=double, tab_id=tab_id)
        return with_tab(f"{'Double-clicked' if double else 'Clicked'} at ({x}, {y}).", result)

    def browser_read_text(
        near: str = "", timeout: float = DEFAULT_WAIT, tab_id: int | str = 0
    ) -> dict[str, Any]:
        """Read the text next to a label on the page -- "Price" gives the block it sits
        in, like "Price ¥89" -- or the whole page's text. In a saved workflow, compare it
        with the last run's (a remember step) to act only when it changed.

        Args:
            near: a label or text on the page; empty reads the whole page
            timeout: seconds to wait for it to appear
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        wait = wait_limit(timeout)
        result = call("read_text", wait + DEFAULT_TIMEOUT, near=near, timeout=wait, tab_id=tab_id)
        text = str(result.get("text") or "")
        return {"text": text, "message": with_tab(text or "(no text)", result)}

    return {
        "browser_screenshot": browser_screenshot,
        "browser_click_at": browser_click_at,
        "browser_read_text": browser_read_text,
    }
