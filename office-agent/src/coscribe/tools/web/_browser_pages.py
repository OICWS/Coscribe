"""What the browser tools say about pages, and the tools that work on several pages at once:
reading them, and listing, opening, selecting and closing tabs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

DEFAULT_TIMEOUT = 30.0
NAVIGATE_TIMEOUT = 60.0
SNAPSHOT_CHARS = 12_000
# Reading many pages at once still shows each enough to tell its state.
_SNAPSHOT_MIN_SHARE = 2_000


def tab_line(tab: Any) -> str:
    if not isinstance(tab, dict):
        return ""
    title = str(tab.get("title") or "").strip() or "(untitled)"
    return f"Tab {tab.get('id')}: {title} -- {tab.get('url') or 'about:blank'}"


def with_tab(message: str, result: dict[str, Any]) -> str:
    """The step's outcome, then what the page now holds open for the model
    to deal with, then the tab it happened in."""
    lines = [message]
    if result.get("note"):
        lines.append(str(result["note"]))
    if result.get("dialog"):
        lines.append(str(result["dialog"]))
    if result.get("file_chooser"):
        lines.append(
            "That opened a file chooser -- choose the files with browser_file_upload(paths=[...])."
        )
    for download in result.get("downloads") or []:
        path, state = download.get("path"), download.get("state")
        if state == "completed":
            lines.append(f"Downloaded {path}")
        elif state == "progressing":
            lines.append(
                f"Downloading {path} -- browser_wait_for(download=True) waits until it's done."
            )
        else:
            lines.append(f"Download of {path}: {state}")
    if result.get("tabs"):
        lines.append("Browser pages changed (new popups stay in the background):")
        for tab in result["tabs"]:
            if isinstance(tab, dict):
                opener = f" (opened by Tab {tab['opener_id']})" if tab.get("opener_id") else ""
                lines.append(f"{'* ' if tab.get('active') else '  '}{tab_line(tab)}{opener}")
        lines.append(
            'Use browser_tabs("select", tab_id=...) to work in another page, '
            'or "close" to close it.'
        )
    if result.get("current_tab"):
        lines.append(f"Current page: {tab_line(result['current_tab'])}")
    line = tab_line(result.get("tab"))
    if line:
        lines.append(line)
    return "\n".join(lines)


def snapshot_tool(call: Callable[..., dict[str, Any]]) -> dict[str, Callable[..., Any]]:
    def read_page(start: int, tab_id: int | str, max_chars: int) -> str:
        result = call("snapshot", start=max(0, start), max_chars=max_chars, tab_id=tab_id)
        text = str(result.get("text") or "")
        total = int(result.get("total_chars") or len(text))
        end = max(0, start) + len(text)
        header = with_tab("", result).strip()
        if end < total:
            more = f"tab_id={tab_id!r}, start={end}" if tab_id else f"start={end}"
            text += (
                f"\n\n[Page continues: {end} of {total} characters shown. "
                f"Call browser_snapshot({more}) for more.]"
            )
        return f"{header}\n\n{text}" if header else text

    def browser_snapshot(
        start: int = 0, tab_id: int | str = 0, tab_ids: list[int | str] | None = None
    ) -> str:
        """Read headings, text, links, buttons and fields in page order.
        Act using fresh [ref=e12] references; take a new snapshot after page changes.
        Actions also accept a role and quoted name as printed here, e.g.
        'checkbox "All items"' (append " #2" for the second). Descriptions wait for
        the action's timeout. Saved workflows must use descriptions because refs
        are numbered afresh on every load.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            start: character offset to continue a long page from (the
                previous snapshot says where it stopped)
            tab_ids: several pages (ids or saved names) to read at once, e.g. to see
                which exports finished; each gets a share of the length
        """
        if not tab_ids:
            return read_page(start, tab_id, SNAPSHOT_CHARS)
        if start:
            raise ValueError("Continue one page at a time: pass tab_id and start, not tab_ids.")
        targets = list(dict.fromkeys(tab_ids))
        share = max(_SNAPSHOT_MIN_SHARE, SNAPSHOT_CHARS // len(targets))

        def one(target: int | str) -> str:
            try:
                return read_page(0, target, share)
            except (ValueError, TimeoutError) as exc:  # one unreadable page must not hide the rest
                return f"Tab {target}: couldn't read it: {exc}"

        # Pages answer in parallel in the desktop app, so the reads overlap here too.
        with ThreadPoolExecutor(max_workers=len(targets)) as pool:
            pages = list(pool.map(one, targets))
        return "\n\n----\n\n".join(pages)

    return {"browser_snapshot": browser_snapshot}


def tab_tools(call: Callable[..., dict[str, Any]]) -> dict[str, Callable[..., Any]]:
    def browser_tabs(
        action: str = "list",
        tab_id: int | str = 0,
        url: str = "",
        name: str = "",
        source_tab: int | str = 0,
        tab_ids: list[int | str] | None = None,
        keep: list[int | str] | None = None,
    ) -> str | dict[str, Any]:
        """Manage up to 16 tabs. Automation selection leaves the user's visible tab alone.
        Other tools use tab_id or that selection. Popups list their opener; close them
        when finished. Use browser_navigate to reuse a tab with a different URL.
        Closing several pages leaves open the ones the user used or took over and
        the ones another step is working in, and says which.

        Args:
            action: "list", "new", "select", "close", "close_all" (every page but
                keep), "info" (structured runtime ids), or "close_downloads"
                (finished unused popup downloads)
            tab_id: runtime id or saved name; "current", "opener" or "last_opened"
            source_tab: optional id or name to scope "opener" or "last_opened";
                specify it in parallel workflows so another lane cannot change the source
            url: for "new"
            name: optional stable name for a new page, reusable as tab_id in any browser tool
            tab_ids: for "close", several pages (ids or saved names) closed in one step
            keep: for "close_all", pages to leave open (ids, saved names or "current")
        """
        if action not in ("list", "new", "select", "close", "close_all", "info", "close_downloads"):
            raise ValueError("Unknown browser tab action.")
        if tab_ids is not None and (action != "close" or not tab_ids):
            raise ValueError('tab_ids lists the pages for "close".')
        if keep is not None and action != "close_all":
            raise ValueError('keep is for "close_all".')
        timeout = NAVIGATE_TIMEOUT if action == "new" and url else DEFAULT_TIMEOUT
        result = call(
            "tabs",
            timeout,
            op=action,
            tab_id=tab_id or None,
            url=url or None,
            name=name or None,
            **({"source_tab": source_tab} if source_tab else {}),
            **({"tab_ids": list(tab_ids)} if tab_ids else {}),
            **({"keep": list(keep)} if keep else {}),
        )
        if action == "info":
            return result
        tabs = result.get("tabs") or []
        lines = _closing_lines(result)
        for tab in tabs:
            if not isinstance(tab, dict):
                continue
            opener = f" (opened by Tab {tab['opener_id']})" if tab.get("opener_id") else ""
            lines.append(f"{'* ' if tab.get('active') else '  '}{tab_line(tab)}{opener}")
        return "\n".join(lines) if lines else "No tabs are open."

    return {"browser_tabs": browser_tabs}


def _closing_lines(result: dict[str, Any]) -> list[str]:
    """What closing several pages did, before the pages still open."""
    lines = []
    if "closed" in result:
        closed = [f"Tab {t.get('id')}" for t in result.get("closed") or [] if isinstance(t, dict)]
        lines.append(f"Closed {', '.join(closed)}." if closed else "Closed no pages.")
    for tab in result.get("kept") or []:
        if isinstance(tab, dict):
            lines.append(f"Left open {tab_line(tab)} -- {tab.get('reason')}.")
    if lines:
        lines.append("Open now:")
    return lines
