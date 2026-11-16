"""The browser_* tools: they drive the tabs in the desktop app's Browser
panel, the same tabs the user sees, so every step happens in front of them
and uses their logins there.

The desktop app (office-agent-desktop, src/main/browserAgent.ts) connects to
this server's /internal/browser-host stream with the token it started the
server with, receives one command at a time and posts each result back.
Commands travel over that connection instead of a remote-debugging port:
a debugging port would let any local process take over those logged-in
pages.

Tool functions run in LangGraph's worker threads, so each call hops onto
the server's event loop (where the connection lives) and blocks on the
reply.
"""

from __future__ import annotations

import asyncio
import base64
import itertools
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ...needs_permission import SITE_MARK, NeedsPermission
from ...runtime import NetworkGuard, tool_metadata
from .._workspace import WorkspaceScope
from ._browser_forms import form_tools, wait_for_any
from ._browser_moves import move_tools
from ._browser_pages import (
    DEFAULT_TIMEOUT,
    DEFAULT_WAIT,
    NAVIGATE_TIMEOUT,
    snapshot_tool,
    tab_tools,
    wait_limit,
    with_tab,
)

# The desktop app may first ask the user whether the AI can use the site
# (it gives up after three minutes), so every call waits that much longer.
_PERMISSION_WAIT = 190.0
_DOWNLOADS_FOLDER = "downloads"
_EVALUATE_CHARS = 5_000

_UNAVAILABLE = (
    "Coscribe's browser isn't reachable right now -- it runs inside the Coscribe "
    "desktop app, which has to be open. Tell the user, or use read_web_page for a "
    "page that doesn't need a login or clicking."
)


class BrowserUnavailableError(ValueError):
    pass


class BrowserHost:
    """The one desktop app connection. A reconnect replaces the previous
    connection, and whatever that one still owed a reply fails, rather
    than waiting on a stream nobody reads any more."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._outbox: asyncio.Queue[dict[str, Any]] | None = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._threads: dict[str, str] = {}
        self._ids = itertools.count(1)

    @property
    def connected(self) -> bool:
        return self._outbox is not None

    def attach(self) -> asyncio.Queue[dict[str, Any]]:
        self._fail_pending("The desktop app reconnected; try the step again.")
        self._loop = asyncio.get_running_loop()
        self._outbox = asyncio.Queue()
        return self._outbox

    def detach(self, outbox: asyncio.Queue[dict[str, Any]]) -> None:
        if self._outbox is outbox:
            self._outbox = None
            self._fail_pending(_UNAVAILABLE)

    def resolve(self, request_id: str, reply: dict[str, Any]) -> bool:
        future = self._pending.pop(request_id, None)
        if future is None or future.done():
            return False
        future.set_result(reply)
        return True

    def _fail_pending(self, message: str) -> None:
        pending, self._pending = self._pending, {}
        self._threads.clear()
        for future in pending.values():
            if not future.done():
                future.set_result({"ok": False, "error": message})

    def set_active(self, thread_id: str, active: bool) -> None:
        """Tell the desktop app a conversation's turn or a workflow run has
        started or ended: a download from its tab in between is saved
        without asking, even one that begins long after the step that set
        it off. Call on the server's loop."""
        if self._outbox is not None:
            self._outbox.put_nowait(
                {"id": "", "thread_id": thread_id, "action": "activity", "args": {"active": active}}
            )

    def cancel(self, thread_id: str) -> None:
        """Stop the conversation's browser step: the desktop app drops it
        (a wait there can run for an hour) and whatever it queued, and the
        tool call waiting on it returns now. Call on the server's loop."""
        if self._outbox is not None:
            self._outbox.put_nowait(
                {"id": "", "thread_id": thread_id, "action": "cancel", "args": {}}
            )
        for request_id in [r for r, t in self._threads.items() if t == thread_id]:
            future = self._pending.pop(request_id, None)
            self._threads.pop(request_id, None)
            if future is not None and not future.done():
                future.set_result({"ok": False, "error": "Stopped by the user."})

    async def request(
        self, action: str, args: dict[str, Any], thread_id: str, timeout: float
    ) -> dict[str, Any]:
        if self._outbox is None:
            raise BrowserUnavailableError(_UNAVAILABLE)
        request_id = str(next(self._ids))
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        self._threads[request_id] = thread_id
        await self._outbox.put(
            {"id": request_id, "thread_id": thread_id, "action": action, "args": args}
        )
        try:
            reply = await asyncio.wait_for(future, timeout)
        except TimeoutError as exc:
            # Cancel this request only: a later step in the same conversation may already exist.
            if self._outbox is not None:
                self._outbox.put_nowait(
                    {
                        "id": "",
                        "thread_id": thread_id,
                        "action": "cancel_request",
                        "args": {"request_id": request_id},
                    }
                )
            raise ValueError(f"The browser didn't finish {action} within {timeout:.0f}s.") from exc
        finally:
            self._pending.pop(request_id, None)
            self._threads.pop(request_id, None)
        if not reply.get("ok"):
            error = str(reply.get("error") or f"The browser couldn't {action}.")
            if error.startswith(SITE_MARK):
                host = error[len(SITE_MARK) :].strip()
                raise NeedsPermission(
                    "site",
                    host,
                    f"{host} isn't a site this workflow is allowed to use. "
                    "Allow it for the workflow, or name it in a step.",
                )
            raise ValueError(error)
        result = reply.get("result")
        return result if isinstance(result, dict) else {}

    def call(
        self,
        action: str,
        args: dict[str, Any],
        thread_id: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        loop = self._loop
        if loop is None or self._outbox is None:
            raise BrowserUnavailableError(_UNAVAILABLE)
        future = asyncio.run_coroutine_threadsafe(
            self.request(action, args, thread_id, timeout), loop
        )
        return future.result(timeout + 5)


BROWSER_HOST = BrowserHost()

# Each conversation and workflow run has tabs of its own in the desktop app, so
# runs in different threads go side by side. Within one thread they share those
# tabs, and two at once would navigate them out from under each other.
_BROWSER_RUNS: dict[str, asyncio.Lock] = {}


def browser_run(thread_id: str) -> asyncio.Lock:
    """The lock a run that drives the browser holds in `thread_id`'s tabs."""
    return _BROWSER_RUNS.setdefault(thread_id, asyncio.Lock())


def _free_path(folder: Path, name: str) -> Path:
    """`name` in `folder`, as "name (1).ext" and so on if taken -- the way
    the browser names a download that would overwrite a file."""
    path = folder / name
    stem, suffix = Path(name).stem, Path(name).suffix
    n = 1
    while path.exists():
        path = folder / f"{stem} ({n}){suffix}"
        n += 1
    return path


SCREENSHOT_FOLDER = "screenshots"


def page_screenshot(
    thread_id: str,
    state_dir: Path,
    host: BrowserHost = BROWSER_HOST,
    *,
    saved_workflow: bool = False,
) -> str | None:
    """The conversation's current page as a PNG under the state folder:
    its file name, or None when there's no page to capture. Blocks; call
    it off the server's loop."""
    args: dict[str, Any] = {"saved_workflow": True} if saved_workflow else {}
    try:
        result = host.call("screenshot", args, thread_id, DEFAULT_TIMEOUT)
    except Exception:  # noqa: BLE001 -- evidence is optional; the run's own result stands
        return None
    png = result.get("png")
    if not isinstance(png, str):
        return None
    folder = state_dir / SCREENSHOT_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.png"
    (folder / name).write_bytes(base64.b64decode(png))
    return name


# The tools are grouped into builders under 100 lines; `build_browser_tools` puts them back in the
# original order, which is the tool-list order the schema snapshot pins.
def _browser_call(
    thread_id: str,
    host: BrowserHost,
    scope: WorkspaceScope | None,
    saved_workflow: bool,
    allowed_sites: Callable[[], list[str]] | None,
    network: NetworkGuard | None,
) -> Callable[..., dict[str, Any]]:
    def call(action: str, limit: float = DEFAULT_TIMEOUT, **args: Any) -> dict[str, Any]:
        if not args.get("tab_id"):
            args.pop("tab_id", None)
        if network is not None:
            network.check_online()
            # The desktop app checks every step against these, as a click can leave the page.
            sites = network.sites()
            if sites is not None:
                args["network_sites"] = sites
        if scope is not None:
            args["download_dir"] = str(scope.root / _DOWNLOADS_FOLDER)
        if saved_workflow:
            args["saved_workflow"] = True
            if allowed_sites is not None:
                args["allowed_sites"] = allowed_sites()
        result = host.call(action, args, thread_id, limit + _PERMISSION_WAIT)
        tab = result.get("tab")
        if "network_sites" in args and isinstance(tab, dict) and network is not None:
            # Where the step ended up: a redirect or a clicked link can leave the list.
            if str(tab.get("url") or "").startswith(("http://", "https://")):
                network.check_url(str(tab["url"]))
        if scope is not None:
            # As the file tools take them: relative to the workspace.
            for download in result.get("downloads") or []:
                path = Path(str(download.get("path")))
                download["path"] = scope.relative(path) if path.is_absolute() else str(path)
        return result

    return call


def _navigation_tools(call: Callable[..., dict[str, Any]]) -> dict[str, Callable[..., Any]]:
    def browser_navigate(url: str, tab_id: int | str = 0) -> str:
        """Navigate coscribe's browser for pages needing login, JavaScript or interaction.
        Reuses the target tab; call browser_snapshot afterwards.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            url: the address; a bare domain like "example.com" works too
        """
        result = call("navigate", NAVIGATE_TIMEOUT, url=url, tab_id=tab_id)
        return with_tab("Loaded.", result)

    def browser_navigate_back(tab_id: int | str = 0) -> str:
        """Go back one page in the current tab of coscribe's browser.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
        """
        return with_tab("Went back.", call("back", tab_id=tab_id))

    def browser_hover(ref: str, timeout: float = DEFAULT_WAIT, tab_id: int | str = 0) -> str:
        """Move the mouse over an element in coscribe's browser, e.g. to open
        a menu that appears on hover.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            ref: the element's ref from the latest browser_snapshot, or its
                description
            timeout: how long a described element may take to appear, in
                seconds (default 30, up to 3600)
        """
        wait = wait_limit(timeout)
        result = call("hover", wait + DEFAULT_TIMEOUT, ref=ref, timeout=wait, tab_id=tab_id)
        return with_tab(f"Hovering over {result.get('element') or ref}.", result)

    def browser_scroll(
        direction: str = "down", ref: str = "", within: str = "", tab_id: int | str = 0
    ) -> str:
        """Scroll the current page in coscribe's browser by about one
        screen, or bring one element into view. Long lists and tables
        often show only the rows in view: scroll, snapshot, repeat until
        what you need appears or nothing moves.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            direction: "down", "up", "left" or "right"
            ref: scroll this element into view instead (from browser_snapshot)
            within: scroll the list, table or pane this element is in (any
                ref inside it) rather than the one in the middle of the view
        """
        if direction not in ("down", "up", "left", "right"):
            raise ValueError('direction must be "down", "up", "left" or "right".')
        result = call(
            "scroll", direction=direction, ref=ref or None, within=within or None, tab_id=tab_id
        )
        return with_tab(str(result.get("note") or "Scrolled."), result)

    return {
        "browser_navigate": browser_navigate,
        "browser_navigate_back": browser_navigate_back,
        "browser_hover": browser_hover,
        "browser_scroll": browser_scroll,
    }


def _input_tools(call: Callable[..., dict[str, Any]]) -> dict[str, Callable[..., Any]]:
    def browser_click(
        ref: str, double: bool = False, timeout: float = DEFAULT_WAIT, tab_id: int | str = 0
    ) -> str:
        """Click an element by snapshot ref or description using normal mouse input.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            ref: the element's ref, e.g. "e12", or its description
            double: double-click instead of a single click
            timeout: how long a described element may take to appear, in
                seconds (default 30, up to 3600)
        """
        wait = wait_limit(timeout)
        result = call(
            "click", wait + DEFAULT_TIMEOUT, ref=ref, double=double, timeout=wait, tab_id=tab_id
        )
        return with_tab(f"Clicked {result.get('element') or ref}.", result)

    def browser_type(
        ref: str,
        text: str,
        submit: bool = False,
        timeout: float = DEFAULT_WAIT,
        tab_id: int | str = 0,
    ) -> str:
        """Type into a text field in coscribe's browser, replacing what's in
        it, by the field's ref from the latest browser_snapshot.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            ref: the field's ref, e.g. "e7", or its description
            text: what to type
            submit: press Enter afterwards (e.g. to run a search)
            timeout: how long a described element may take to appear, in
                seconds (default 30, up to 3600)
        """
        wait = wait_limit(timeout)
        result = call(
            "type",
            wait + DEFAULT_TIMEOUT,
            ref=ref,
            text=text,
            submit=submit,
            timeout=wait,
            tab_id=tab_id,
        )
        return with_tab(f"Typed into {result.get('element') or ref}.", result)

    def browser_press_key(key: str, tab_id: int | str = 0) -> str:
        """Press a key in coscribe's browser, on whatever has focus -- e.g.
        "Enter", "Escape", "Tab", "ArrowDown", "PageDown", "Backspace",
        "F1".."F12", or a combination like "Control+a" or "Shift+F4".

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            key: the key or combination
        """
        return with_tab(f"Pressed {key}.", call("press_key", key=key, tab_id=tab_id))

    def browser_select_option(
        ref: str, values: list[str], timeout: float = DEFAULT_WAIT, tab_id: int | str = 0
    ) -> str:
        """Choose option(s) in a dropdown (<select>) in coscribe's browser.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            ref: the dropdown's ref from the latest browser_snapshot, or
                its description
            values: the options to choose, by their visible text or value
            timeout: how long a described element may take to appear, in
                seconds (default 30, up to 3600)
        """
        wait = wait_limit(timeout)
        result = call(
            "select_option",
            wait + DEFAULT_TIMEOUT,
            ref=ref,
            values=values,
            timeout=wait,
            tab_id=tab_id,
        )
        chosen = ", ".join(str(v) for v in result.get("selected") or values)
        return with_tab(f"Selected {chosen}.", result)

    return {
        "browser_click": browser_click,
        "browser_type": browser_type,
        "browser_press_key": browser_press_key,
        "browser_select_option": browser_select_option,
    }


def _waiting_tools(
    call: Callable[..., dict[str, Any]], scope: WorkspaceScope | None
) -> dict[str, Callable[..., Any]]:
    def browser_wait_for(
        text: str = "",
        gone: str = "",
        element: str = "",
        download: bool = False,
        seconds: float = 0,
        timeout: float = DEFAULT_WAIT,
        save_to: str = "",
        tab_id: int | str = 0,
        any_of: list[str] | None = None,
    ) -> str | dict[str, Any]:
        """Wait in coscribe's browser for one thing: text to appear, text to
        go away (e.g. "Loading…"), an element to appear, or a download to
        finish -- or just for some seconds. Use it for anything slow, like
        a report or export that takes minutes.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            text: wait until this text is on the page
            gone: wait until this text is no longer on the page
            element: wait until this element is there, as the snapshot
                prints it, e.g. 'button "Download"'
            download: wait until the page's download (started earlier or
                while waiting) has finished; the result's "file" is where
                it was saved -- the name changes from run to run
            seconds: just wait this long
            timeout: give up after this many seconds (default 30, up to 3600)
            save_to: with download, a folder to move the file into (the
                workspace's downloads/ otherwise); one you can write to
            any_of: wait until any of these texts appears (e.g. a success and an
                error message); the result's "found" says which one
        """
        if any_of is not None:
            return wait_for_any(
                call, any_of, [text, gone, element, download, save_to], timeout, tab_id
            )
        if save_to and not download:
            raise ValueError("save_to goes with download=True.")
        folder = None
        if save_to:
            if scope is None:
                raise ValueError("Saving downloads elsewhere isn't available in this conversation.")
            # Before waiting: a folder outside the allowed ones should fail
            # now, not after a twenty-minute export.
            folder = scope.resolve(save_to, write=True)
        chosen = [n for n, v in (("text", text), ("gone", gone), ("element", element)) if v]
        if download:
            chosen.append("download")
        if len(chosen) > 1:
            raise ValueError(f"Wait for one thing at a time, not {' and '.join(chosen)}.")
        limit = wait_limit(max(timeout, seconds))
        if not chosen:
            if seconds <= 0:
                raise ValueError("Pass text, gone, element or download=True -- or seconds.")
            result = call("wait_for", seconds + 10, seconds=seconds, timeout=limit, tab_id=tab_id)
            return with_tab(f"Waited {seconds:g}s.", result)
        result = call(
            "wait_for",
            limit + 15,
            text=text or None,
            gone=gone or None,
            element=element or None,
            download=download,
            timeout=limit,
            tab_id=tab_id,
        )
        if download:
            # A saved workflow's next step reads the file from here: the
            # name a site gives an export changes run to run.
            done = [d for d in result.get("downloads") or [] if d.get("state") == "completed"]
            if folder is not None and scope is not None:
                folder.mkdir(parents=True, exist_ok=True)
                for item in done:
                    source = scope.resolve(str(item.get("path")))
                    target = _free_path(folder, str(item.get("name") or source.name))
                    shutil.move(str(source), target)
                    item["path"] = scope.relative(target)
            files = [str(item.get("path")) for item in done]
            return {
                "file": files[-1] if files else "",
                "files": files,
                "message": with_tab("The download finished.", result),
            }
        if element:
            message = f"{element} is on the page."
        elif gone:
            message = f'"{gone}" is gone from the page.'
        else:
            message = f'"{text}" is on the page.'
        return with_tab(message, result)

    return {
        "browser_wait_for": browser_wait_for,
    }


def _page_tools(
    call: Callable[..., dict[str, Any]], scope: WorkspaceScope | None
) -> dict[str, Callable[..., Any]]:
    def browser_handle_dialog(accept: bool = True, tab_id: int | str = 0) -> str:
        """Answer the alert or confirm dialog open on the current page in
        coscribe's browser (a step's result says when one opened; the page
        waits until it's answered).

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            accept: OK (True) or Cancel (False)
        """
        result = call("handle_dialog", accept=accept, tab_id=tab_id)
        kind = str(result.get("dialog_type") or "dialog")
        answer = "Accepted" if result.get("accepted", accept) else "Dismissed"
        return with_tab(f'{answer} the {kind}: "{result.get("message") or ""}".', result)

    def browser_file_upload(
        paths: list[str], ref: str = "", tab_id: int | str = 0, drop: bool = False
    ) -> str:
        """Upload files from the user's folders to the page in coscribe's
        browser, as if the user had picked them. Pass the ref of the upload
        button or file field; leave ref empty to answer a file chooser a
        click just opened.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            paths: the files, relative to the workspace or absolute under a
                folder you can read
            ref: the upload button or file field from browser_snapshot
            drop: drag the files onto ref instead, for an area that says
                "drop files here" and has no button
        """
        if drop and not ref:
            raise ValueError("Pass the ref of the area to drop the files on.")
        if not paths:
            raise ValueError("Pass at least one file in paths.")
        if scope is None:
            raise ValueError("Uploading files isn't available in this conversation.")
        files = []
        for path in paths:
            resolved = scope.resolve(path)
            if not resolved.is_file():
                raise ValueError(f"No such file: {path}")
            files.append(str(resolved))
        result = call("upload", ref=ref or None, paths=files, tab_id=tab_id, drop=drop)
        names = ", ".join(scope.relative(Path(f)) for f in files)
        return with_tab(f"Uploaded {names} to {result.get('element') or 'the page'}.", result)

    def browser_evaluate(expression: str, tab_id: int | str = 0) -> str:
        """Run a JavaScript expression in the current page of coscribe's
        browser, as the page's own scripts would, and return its value
        (awaited if it's a promise). For reading what a snapshot doesn't
        show or doing what clicks can't; prefer the other browser_* tools
        when they can do the job.

        Args:
            tab_id: runtime tab id or saved name; 0 uses the automation-selected page
            expression: e.g. "document.title" or
                "[...document.querySelectorAll('h2')].map(h => h.textContent)"
        """
        if not expression.strip():
            raise ValueError("Pass a JavaScript expression.")
        result = call("evaluate", expression=expression, tab_id=tab_id)
        value = str(result.get("value") if result.get("value") is not None else "null")
        if len(value) > _EVALUATE_CHARS:
            value = (
                f"{value[:_EVALUATE_CHARS]}\n[... {len(value) - _EVALUATE_CHARS} more "
                "characters -- return less, e.g. a slice or a count]"
            )
        return with_tab(value, result)

    return {
        "browser_handle_dialog": browser_handle_dialog,
        "browser_file_upload": browser_file_upload,
        "browser_evaluate": browser_evaluate,
    }


def build_browser_tools(
    thread_id: str,
    host: BrowserHost = BROWSER_HOST,
    *,
    scope: WorkspaceScope | None = None,
    saved_workflow: bool = False,
    allowed_sites: Callable[[], list[str]] | None = None,
    network: NetworkGuard | None = None,
) -> list[Callable[..., Any]]:
    """`saved_workflow`: these tools run a saved workflow's steps, which
    the user reviewed and saved -- consent to the sites they visit -- so
    the desktop app doesn't stop an unattended run to ask. `allowed_sites`
    (read at each call, since a run may be allowed one more while it waits)
    is what that consent covers: a site outside it is refused with
    NeedsPermission instead. `network`: the conversation's network setting,
    which no consent widens."""

    call = _browser_call(thread_id, host, scope, saved_workflow, allowed_sites, network)
    fns = {
        **form_tools(call),
        **move_tools(call),
        **tab_tools(call),
        **snapshot_tool(call),
        **_navigation_tools(call),
        **_input_tools(call),
        **_waiting_tools(call, scope),
        **_page_tools(call, scope),
    }
    read = [
        fns["browser_navigate"],
        fns["browser_navigate_back"],
        fns["browser_snapshot"],
        fns["browser_hover"],
        fns["browser_scroll"],
        fns["browser_wait_for"],
        fns["browser_tabs"],
        fns["browser_copy"],
    ]
    act = [
        fns["browser_click"],
        fns["browser_type"],
        fns["browser_fill_form"],
        fns["browser_steps"],
        fns["browser_drag"],
        fns["browser_paste"],
        fns["browser_press_key"],
        fns["browser_select_option"],
        fns["browser_handle_dialog"],
        fns["browser_file_upload"],
    ]
    return (
        [tool_metadata(f, risk_category="READ", category="browser") for f in read]
        + [tool_metadata(f, risk_category="EXTERNAL", category="browser") for f in act]
        # Arbitrary script with the user's logins behind it.
        + [tool_metadata(fns["browser_evaluate"], risk_category="EXEC", category="browser")]
    )
