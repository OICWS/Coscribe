"""Dragging on a page, and copying and pasting through the AI's own clipboard: one per
conversation or run in the desktop app, never the person's, which may hold their passwords
and which a copy would overwrite (the maintainer's choice, #915)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ._browser_pages import DEFAULT_TIMEOUT, DEFAULT_WAIT, wait_limit, with_tab


def move_tools(call: Callable[..., dict[str, Any]]) -> dict[str, Callable[..., Any]]:
    def browser_drag(
        ref: str,
        target: str = "",
        by_x: int = 0,
        by_y: int = 0,
        timeout: float = DEFAULT_WAIT,
        tab_id: int | str = 0,
    ) -> str:
        """Drag an element with the mouse: onto another element (a card to a column, a
        row to a new place), or by some pixels (a slider, a splitter). Files from the
        user's folders are dropped with browser_file_upload(drop=True) instead.

        Args:
            ref: what to drag, as a snapshot ref or description
            target: where to drop it, as a ref or description
            by_x: without a target, how far right to drag (negative: left)
            by_y: without a target, how far down to drag (negative: up)
            timeout: seconds to wait for the elements
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        if bool(target) == bool(by_x or by_y):
            raise ValueError("Give a target, or by_x/by_y, not both and not neither.")
        wait = wait_limit(timeout)
        result = call("drag", wait * 2 + DEFAULT_TIMEOUT, ref=ref, target=target or None,
                      by_x=by_x, by_y=by_y, timeout=wait)  # fmt: skip
        onto = f" onto {result['onto']}" if result.get("onto") else ""
        return with_tab(f"Dragged {result.get('element') or ref}{onto}.", result)

    def browser_copy(ref: str = "", tab_id: int | str = 0) -> str:
        """Copy an element's text (and its formatting) to the AI's own clipboard, or the
        page's selection when ref is empty; browser_paste puts it into a field on any
        page of this conversation. The user's own clipboard is never read or changed.

        Args:
            ref: the element to copy, as a snapshot ref or description
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        result = call("copy", ref=ref or None, tab_id=tab_id)
        preview = str(result.get("preview") or "")
        more = "…" if int(result.get("chars") or 0) > len(preview) else ""
        return with_tab(f'Copied {result.get("chars")} characters: "{preview}{more}"', result)

    def browser_paste(ref: str, plain: bool = False, tab_id: int | str = 0) -> str:
        """Paste what browser_copy copied into a field, replacing what it holds. A rich
        text editor keeps the formatting unless plain is true.

        Args:
            ref: the field to paste into, as a snapshot ref or description
            plain: paste the text only, even into a rich text editor
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        result = call("paste", ref=ref, plain=plain, tab_id=tab_id)
        how = " with its formatting" if result.get("formatted") else ""
        return with_tab(f"Pasted into {result.get('element') or ref}{how}.", result)

    return {
        "browser_drag": browser_drag,
        "browser_copy": browser_copy,
        "browser_paste": browser_paste,
    }
