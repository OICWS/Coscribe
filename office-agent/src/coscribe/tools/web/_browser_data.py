"""Taking data off a page into the person's folders: a table or list as a CSV, gathered across
its pages or as it loads more on scrolling, and the page as a PDF. A workbook is made from the
CSV by the spreadsheet tools, which own how a workbook is written (decision 0011)."""

from __future__ import annotations

import base64
import csv
import io
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .._workspace import WorkspaceScope
from ._browser_pages import (
    DEFAULT_TIMEOUT,
    DEFAULT_WAIT,
    SNAPSHOT_CHARS,
    free_path,
    wait_limit,
    with_tab,
)

MAX_PAGES = 100
_PREVIEW_ROWS = 5
_NUMBER = re.compile(r"^[+-]?(\d[\d,]*)?(\.\d+)?%?$")


def _safe_cell(value: Any) -> str:
    """A page's text as a CSV cell. Excel runs a cell that starts with = + - @ as a formula,
    so a page could plant one (a link that sends data away); such text gets a leading '.
    Numbers like -12.5 stay numbers."""
    text = str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r") and not _NUMBER.fullmatch(text):
        return "'" + text
    return text


def _output(scope: WorkspaceScope | None, path: str, suffix: str) -> Path:
    if scope is None:
        raise ValueError("Saving files isn't available in this conversation.")
    if not path.strip():
        raise ValueError(f"Pass the path of the {suffix} file to write.")
    if Path(path).suffix.lower() != suffix:
        path = f"{path}{suffix}"
    target = scope.resolve(path, write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    # A workflow that runs every day keeps each day's file.
    return free_path(target.parent, target.name)


def _rows_text(header: list[str] | None, rows: list[list[str]], limit: int) -> str:
    lines = ["\t".join(header)] if header else []
    shown = 0
    for row in rows[:limit]:
        lines.append("\t".join(row))
        shown += 1
    text = "\n".join(lines)
    if len(text) > SNAPSHOT_CHARS:
        text = text[:SNAPSHOT_CHARS].rsplit("\n", 1)[0]
        shown = text.count("\n") + (0 if header else 1)
    if shown < len(rows):
        text += f"\n[... {len(rows) - shown} more rows -- pass path to save them all]"
    return text


def _ending(result: dict[str, Any], max_pages: int) -> str:
    pages = int(result.get("pages") or 1)
    read = f" from {pages} pages" if pages > 1 else ""
    if result.get("stopped") == "max_pages":
        return f"{read}; stopped at max_pages={max_pages}, so there may be more"
    if result.get("stopped") == "rows":
        return f"{read}; stopped at the row limit"
    return read


def data_tools(
    call: Callable[..., dict[str, Any]], scope: WorkspaceScope | None
) -> dict[str, Callable[..., Any]]:
    def browser_save_table(
        table: str = "",
        path: str = "",
        next_page: str = "",
        scroll: bool = False,
        max_pages: int = 10,
        timeout: float = DEFAULT_WAIT,
        tab_id: int | str = 0,
    ) -> dict[str, Any] | str:
        """Read a table or list off the page as rows, optionally across its pages, and
        save it as a CSV (for Excel, then write_xlsx_cells with from_csv). A list or a
        grid of cards gives one row per item, its lines as columns, and the item's
        link first when items have links.

        Args:
            table: a text inside the table or list, like a column header; empty takes
                the page's largest table
            path: the .csv file to write, relative to the workspace; empty returns
                the rows instead
            next_page: the Next button, as a ref or description, clicked until it is
                gone or disabled or the table stops changing
            scroll: for a list that loads more as it scrolls
            max_pages: with next_page or scroll, at most this many pages (up to 100)
            timeout: seconds to wait for each page
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        if next_page and scroll:
            raise ValueError("Give next_page or scroll, not both.")
        if not 1 <= max_pages <= MAX_PAGES:
            raise ValueError(f"max_pages is from 1 to {MAX_PAGES}.")
        target = _output(scope, path, ".csv") if path else None
        wait = wait_limit(timeout)
        pages = max_pages if next_page or scroll else 1
        result = call("save_table", wait * (pages + 1) + DEFAULT_TIMEOUT, table=table,
                      next_page=next_page or None, scroll=scroll, max_pages=pages,
                      timeout=wait, tab_id=tab_id)  # fmt: skip
        header = [str(h) for h in result.get("header") or []] or None
        rows = [[str(cell) for cell in row] for row in result.get("rows") or []]
        count = f"{len(rows)} row{'s' if len(rows) != 1 else ''}{_ending(result, max_pages)}"
        if target is None:
            return with_tab(f"Read {count}:\n{_rows_text(header, rows, len(rows))}", result)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        for row in ([header] if header else []) + rows:
            writer.writerow([_safe_cell(cell) for cell in row])
        # With a BOM, Excel opens it as UTF-8 and Chinese text reads right.
        target.write_bytes(buffer.getvalue().encode("utf-8-sig"))
        name = scope.relative(target) if scope is not None else str(target)
        preview = _rows_text(header, rows, _PREVIEW_ROWS)
        message = with_tab(f"Saved {count} to {name}. The first rows:\n{preview}", result)
        return {"file": name, "rows": len(rows), "message": message}

    def browser_save_pdf(
        path: str, landscape: bool = False, tab_id: int | str = 0
    ) -> dict[str, Any]:
        """Save the page as a PDF, as printing it would, with its backgrounds.

        Args:
            path: the .pdf file to write, relative to the workspace
            landscape: print the page sideways, for a wide table
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        target = _output(scope, path, ".pdf")
        result = call("save_pdf", DEFAULT_TIMEOUT * 2, landscape=landscape, tab_id=tab_id)
        if not result.get("pdf"):
            raise ValueError("The page couldn't be printed to a PDF.")
        target.write_bytes(base64.b64decode(str(result["pdf"])))
        name = scope.relative(target) if scope is not None else str(target)
        return {"file": name, "message": with_tab(f"Saved the page as {name}.", result)}

    return {"browser_save_table": browser_save_table, "browser_save_pdf": browser_save_pdf}
