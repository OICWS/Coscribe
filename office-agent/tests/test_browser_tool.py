from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest

from coscribe.config import Settings
from coscribe.coordinator import build_coordinator_agent
from coscribe.runtime import get_tool_metadata
from coscribe.tools.web.browser import BrowserHost, BrowserUnavailableError, build_browser_tools


class _FakeHost(BrowserHost):
    def __init__(self, replies: dict[str, dict[str, Any]]) -> None:
        super().__init__()
        self.replies = replies
        self.calls: list[tuple[str, dict[str, Any], str]] = []

    def call(
        self, action: str, args: dict[str, Any], thread_id: str, timeout: float = 30
    ) -> dict[str, Any]:
        self.calls.append((action, args, thread_id))
        return self.replies.get(action, {})


def _tools(host: BrowserHost) -> dict[str, Any]:
    return {tool.__name__: tool for tool in build_browser_tools("t1", host)}


class _ServerLoop:
    """The server's event loop, running in its own thread the way uvicorn's
    does while tool calls arrive from LangGraph's worker threads."""

    def __enter__(self) -> asyncio.AbstractEventLoop:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever)
        self.thread.start()
        return self.loop

    def __exit__(self, *exc: object) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(5)
        self.loop.close()


def _connect_desktop_app(
    host: BrowserHost, loop: asyncio.AbstractEventLoop, reply: dict[str, Any]
) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []

    async def desktop_app() -> None:
        outbox = host.attach()
        command = await outbox.get()
        seen.append(command)
        host.resolve(command["id"], reply)

    asyncio.run_coroutine_threadsafe(desktop_app(), loop)
    for _ in range(100):
        if host.connected:
            break
        threading.Event().wait(0.01)
    return seen


def test_a_call_waits_for_the_desktop_apps_reply() -> None:
    host = BrowserHost()
    with _ServerLoop() as loop:
        seen = _connect_desktop_app(host, loop, {"ok": True, "result": {"tab": {"id": 1}}})
        result = host.call("navigate", {"url": "u"}, "t1", timeout=5)

    assert result == {"tab": {"id": 1}}
    assert seen[0]["action"] == "navigate"
    assert seen[0]["args"] == {"url": "u"}
    assert seen[0]["thread_id"] == "t1"


def test_an_error_reply_reaches_the_model_as_the_tools_error() -> None:
    host = BrowserHost()
    with _ServerLoop() as loop:
        _connect_desktop_app(host, loop, {"ok": False, "error": "No element with ref e9."})
        with pytest.raises(ValueError, match="No element with ref e9"):
            host.call("click", {"ref": "e9"}, "t1", timeout=5)


def test_without_the_desktop_app_the_tools_say_so() -> None:
    with pytest.raises(BrowserUnavailableError, match="desktop app"):
        _tools(BrowserHost())["browser_snapshot"]()


def test_disconnecting_fails_whatever_was_waiting() -> None:
    host = BrowserHost()

    async def scenario() -> dict[str, Any]:
        outbox = host.attach()
        pending = asyncio.create_task(host.request("snapshot", {}, "t1", timeout=5))
        await outbox.get()
        host.detach(outbox)
        try:
            return await pending
        except ValueError as exc:
            return {"error": str(exc)}

    result = asyncio.run(scenario())
    assert "desktop app" in result["error"]
    assert not host.connected


def test_snapshot_shows_the_tab_and_where_a_long_page_continues() -> None:
    host = _FakeHost(
        {
            "snapshot": {
                "text": '- link "News" [ref=e1]',
                "total_chars": 30_000,
                "tab": {"id": 2, "title": "Example", "url": "https://example.com/"},
            }
        }
    )
    output = _tools(host)["browser_snapshot"](start=100)

    assert output.startswith("Tab 2: Example -- https://example.com/")
    assert '- link "News" [ref=e1]' in output
    assert "browser_snapshot(start=122)" in output
    assert host.calls[0] == ("snapshot", {"start": 100, "max_chars": 12_000}, "t1")


def test_click_names_the_element_it_clicked() -> None:
    host = _FakeHost({"click": {"element": 'button "Search"', "tab": {"id": 1, "url": "u"}}})
    assert _tools(host)["browser_click"]("e4").startswith('Clicked button "Search".')


def test_tabs_marks_the_current_one() -> None:
    host = _FakeHost(
        {
            "tabs": {
                "tabs": [
                    {"id": 1, "title": "A", "url": "https://a/", "active": False},
                    {"id": 2, "title": "B", "url": "https://b/", "active": True},
                ]
            }
        }
    )
    output = _tools(host)["browser_tabs"]()
    assert output.splitlines() == ["  Tab 1: A -- https://a/", "* Tab 2: B -- https://b/"]


def test_tabs_accepts_named_runtime_targets() -> None:
    host = _FakeHost({})
    _tools(host)["browser_tabs"]("select", tab_id="report")
    assert host.calls[0][1]["tab_id"] == "report"


def test_acting_on_a_page_needs_approval_reading_it_does_not() -> None:
    tools = _tools(_FakeHost({}))
    risks = {name: get_tool_metadata(tool).risk_category for name, tool in tools.items()}
    assert risks["browser_click"] == "EXTERNAL"
    assert risks["browser_type"] == "EXTERNAL"
    assert risks["browser_snapshot"] == "READ"
    assert risks["browser_navigate"] == "READ"


def _coordinator_tools(tmp_path: Path, **overrides: object) -> tuple[set[str], str]:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        default_model="fake:model",
        workspace_root=tmp_path / "ws",
        state_dir=tmp_path / "state",
        skills_dir=tmp_path / "skills",
        memory_path=tmp_path / "MEMORY.md",
        **overrides,  # type: ignore[arg-type]
    )
    agent = build_coordinator_agent(settings, thread_id="t1")
    return {getattr(t, "__name__", "") for t in agent.tools}, agent.instructions


def test_browser_tools_are_only_offered_inside_the_desktop_app(tmp_path: Path) -> None:
    names, instructions = _coordinator_tools(tmp_path)
    assert "browser_click" not in names
    assert "browser_* tools" not in instructions

    names, instructions = _coordinator_tools(tmp_path, browser_host_token="secret")
    assert {"browser_navigate", "browser_snapshot", "browser_click"} <= names
    assert "browser_* tools" in instructions


def test_a_step_that_opens_a_dialog_says_so() -> None:
    host = _FakeHost(
        {
            "click": {
                "element": 'button "Delete"',
                "dialog": 'A confirm dialog is open on the page: "Sure?". Answer it with '
                "browser_handle_dialog before anything else.",
            }
        }
    )
    out = _tools(host)["browser_click"]("e3")
    assert out.splitlines()[0] == 'Clicked button "Delete".'
    assert "browser_handle_dialog" in out


def test_handle_dialog_passes_the_answer() -> None:
    host = _FakeHost(
        {"handle_dialog": {"dialog_type": "confirm", "message": "Delete?", "accepted": False}}
    )
    out = _tools(host)["browser_handle_dialog"](accept=False)
    assert host.calls[0][:2] == ("handle_dialog", {"accept": False})
    assert out == 'Dismissed the confirm: "Delete?".'


def test_a_click_that_opens_a_file_chooser_points_to_upload() -> None:
    out = _tools(_FakeHost({"click": {"file_chooser": True}}))["browser_click"]("e5")
    assert "browser_file_upload" in out


def test_upload_sends_resolved_files_inside_the_workspace(tmp_path: Path) -> None:
    from coscribe.tools._workspace import WorkspaceScope

    (tmp_path / "report.pdf").write_bytes(b"%PDF")
    host = _FakeHost({"upload": {"element": 'button "Attach"'}})
    tools = {t.__name__: t for t in build_browser_tools("t1", host, scope=WorkspaceScope(tmp_path))}
    out = tools["browser_file_upload"](["report.pdf"], ref="e9")
    action, args, _ = host.calls[0]
    assert action == "upload"
    assert args["ref"] == "e9"
    assert args["paths"] == [str((tmp_path / "report.pdf").resolve())]
    assert out.startswith('Uploaded report.pdf to button "Attach".')

    with pytest.raises(ValueError, match="No such file"):
        tools["browser_file_upload"](["missing.pdf"])
    outside = tmp_path.parent / "secret.txt"
    with pytest.raises(PermissionError):
        tools["browser_file_upload"]([str(outside)])
    assert len(host.calls) == 1


def test_upload_without_a_workspace_is_refused() -> None:
    with pytest.raises(ValueError, match="isn't available"):
        _tools(_FakeHost({}))["browser_file_upload"](["a.txt"])


def test_evaluate_returns_the_value_clipped() -> None:
    host = _FakeHost({"evaluate": {"value": "x" * 6000}})
    out = _tools(host)["browser_evaluate"]("'x'.repeat(6000)")
    assert out.startswith("x" * 5000 + "\n[... 1000 more characters")


def test_evaluate_runs_only_with_approval() -> None:
    tools = _tools(_FakeHost({}))
    assert get_tool_metadata(tools["browser_evaluate"]).risk_category == "EXEC"
    assert get_tool_metadata(tools["browser_file_upload"]).risk_category == "EXTERNAL"
    assert get_tool_metadata(tools["browser_handle_dialog"]).risk_category == "EXTERNAL"


def test_a_step_that_downloads_names_the_file() -> None:
    host = _FakeHost(
        {
            "click": {
                "element": 'button "OK"',
                "downloads": [
                    {"path": "C:\\Users\\me\\Downloads\\EXPORT.XLSX", "state": "completed"},
                    {"path": "C:\\Users\\me\\Downloads\\big.zip", "state": "interrupted"},
                ],
            }
        }
    )
    lines = _tools(host)["browser_click"]("e4").splitlines()
    assert lines[1:] == [
        "Downloaded C:\\Users\\me\\Downloads\\EXPORT.XLSX",
        "Download of C:\\Users\\me\\Downloads\\big.zip: interrupted",
    ]


def test_stop_cancels_the_conversations_step_on_both_ends() -> None:
    host = BrowserHost()

    async def scenario() -> tuple[str, list[dict[str, Any]], bool]:
        outbox = host.attach()
        mine = asyncio.create_task(host.request("wait_for", {}, "t1", timeout=60))
        other = asyncio.create_task(host.request("snapshot", {}, "t2", timeout=60))
        sent = [await outbox.get(), await outbox.get()]
        host.cancel("t1")
        sent.append(await outbox.get())
        try:
            await mine
            error = ""
        except ValueError as exc:
            error = str(exc)
        still_waiting = not other.done()
        other.cancel()
        return error, sent, still_waiting

    error, sent, still_waiting = asyncio.run(scenario())
    assert error == "Stopped by the user."
    assert sent[-1]["action"] == "cancel" and sent[-1]["thread_id"] == "t1"
    # Another conversation's step carries on.
    assert still_waiting


def test_downloads_go_to_the_workspace_and_come_back_relative(tmp_path: Path) -> None:
    from coscribe.tools._workspace import WorkspaceScope

    saved = tmp_path / "downloads" / "EXPORT.XLSX"
    host = _FakeHost(
        {
            "click": {"downloads": [{"path": str(saved), "state": "completed"}]},
            "wait_for": {"downloads": [{"path": str(saved), "state": "completed"}]},
        }
    )
    tools = {t.__name__: t for t in build_browser_tools("t1", host, scope=WorkspaceScope(tmp_path))}
    out = tools["browser_click"]('button "Export"')
    action, args, _ = host.calls[0]
    assert args["download_dir"] == str(tmp_path.resolve() / "downloads")
    assert args["timeout"] == 30
    assert "Downloaded downloads/EXPORT.XLSX" in out

    waited = tools["browser_wait_for"](download=True, timeout=1800)
    assert host.calls[1][1]["download"] is True and host.calls[1][1]["timeout"] == 1800
    assert waited["file"] == "downloads/EXPORT.XLSX"
    assert waited["message"].startswith("The download finished.")


def test_a_slow_download_is_announced_with_how_to_wait_for_it() -> None:
    host = _FakeHost({"click": {"downloads": [{"path": "big.zip", "state": "progressing"}]}})
    out = _tools(host)["browser_click"]("e4")
    assert "Downloading big.zip -- browser_wait_for(download=True)" in out


def test_wait_for_takes_one_thing_and_caps_the_timeout() -> None:
    host = _FakeHost({})
    wait_for = _tools(host)["browser_wait_for"]
    with pytest.raises(ValueError, match="one thing at a time"):
        wait_for(text="Done", download=True)
    with pytest.raises(ValueError, match="seconds"):
        wait_for()
    wait_for(gone="Loading", timeout=99999)
    assert host.calls[-1][1]["gone"] == "Loading"
    assert host.calls[-1][1]["timeout"] == 3600


def test_a_download_wait_moves_the_file_where_asked(tmp_path: Path) -> None:
    from coscribe.tools._workspace import WorkspaceScope

    (tmp_path / "downloads").mkdir()
    (tmp_path / "downloads" / "EXPORT (3).XLSX").write_bytes(b"PK")
    (tmp_path / "exports").mkdir()
    (tmp_path / "exports" / "EXPORT.XLSX").write_bytes(b"old")
    host = _FakeHost(
        {
            "wait_for": {
                "downloads": [
                    {
                        "path": "downloads/EXPORT (3).XLSX",
                        "name": "EXPORT.XLSX",
                        "state": "completed",
                    }
                ]
            }
        }
    )
    tools = {t.__name__: t for t in build_browser_tools("t1", host, scope=WorkspaceScope(tmp_path))}
    waited = tools["browser_wait_for"](download=True, save_to="exports")
    # Never over an earlier export.
    assert waited["file"] == "exports/EXPORT (1).XLSX"
    assert (tmp_path / "exports" / "EXPORT (1).XLSX").read_bytes() == b"PK"
    # Named as the site named it, not after the staging folder's clashes.
    assert not (tmp_path / "downloads" / "EXPORT (3).XLSX").exists()
    assert "Downloaded exports/EXPORT (1).XLSX" in waited["message"]


def test_a_save_folder_outside_the_workspace_fails_before_waiting(tmp_path: Path) -> None:
    from coscribe.tools._workspace import WorkspaceScope

    host = _FakeHost({})
    tools = {
        t.__name__: t
        for t in build_browser_tools("t1", host, scope=WorkspaceScope(tmp_path / "ws"))
    }
    with pytest.raises(PermissionError):
        tools["browser_wait_for"](download=True, save_to=str(tmp_path / "elsewhere"))
    assert host.calls == []
    with pytest.raises(ValueError, match="goes with download"):
        tools["browser_wait_for"](text="Done", save_to="exports")


def test_a_turn_or_run_tells_the_desktop_app_when_it_starts_and_ends() -> None:
    from coscribe.conversation.turn_lock import TurnLock

    host = BrowserHost()

    async def scenario() -> list[dict[str, Any]]:
        outbox = host.attach()
        lock = TurnLock(lambda active: host.set_active("t1", active))
        async with lock:
            assert lock.locked()
        return [outbox.get_nowait(), outbox.get_nowait()]

    sent = asyncio.run(scenario())
    assert [(m["action"], m["thread_id"], m["args"]) for m in sent] == [
        ("activity", "t1", {"active": True}),
        ("activity", "t1", {"active": False}),
    ]


async def test_timeout_cancels_only_its_request_and_keeps_later_steps() -> None:
    host = BrowserHost()
    outbox = host.attach()
    first = asyncio.create_task(host.request("snapshot", {}, "t1", timeout=0.01))
    command = await outbox.get()
    later = asyncio.create_task(host.request("tabs", {}, "t1", timeout=5))
    next_command = await outbox.get()
    with pytest.raises(ValueError, match="didn't finish snapshot"):
        await first
    cancel = await outbox.get()
    assert cancel == {
        "id": "",
        "thread_id": "t1",
        "action": "cancel_request",
        "args": {"request_id": command["id"]},
    }
    assert not host.resolve(command["id"], {"ok": True, "result": {}})
    host.resolve(next_command["id"], {"ok": True, "result": {"tabs": []}})
    assert await later == {"tabs": []}


def test_popup_feedback_names_the_source_and_how_to_select_or_close() -> None:
    host = _FakeHost(
        {
            "click": {
                "element": 'button "Export"',
                "tab": {"id": 1, "url": "https://source/"},
                "tabs": [
                    {"id": 1, "url": "https://source/", "active": True},
                    {"id": 2, "url": "https://popup/", "opener_id": 1},
                ],
            }
        }
    )
    output = _tools(host)["browser_click"]("e1")
    assert "Browser pages changed" in output
    assert "opened by Tab 1" in output
    assert 'browser_tabs("select"' in output
    assert '"close"' in output


def test_tab_list_preserves_popup_relationships() -> None:
    host = _FakeHost(
        {
            "tabs": {
                "tabs": [
                    {"id": 2, "url": "https://popup/", "opener_id": 1, "active": True},
                ]
            }
        }
    )
    assert "opened by Tab 1" in _tools(host)["browser_tabs"]()


@pytest.mark.parametrize("saved_workflow", [False, True])
def test_batch_fill_uses_one_targeted_command(saved_workflow: bool) -> None:
    host = _FakeHost({"fill_form": {}})
    fields = [
        {"ref": "Company Code", "text": "1000"},
        {"ref": "Posting Date", "text": "2026-11-16"},
    ]
    tools = {
        tool.__name__: tool
        for tool in build_browser_tools("t1", host, saved_workflow=saved_workflow)
    }
    tools["browser_fill_form"](fields, tab_id="reports")
    assert len(host.calls) == 1
    assert host.calls[0][0] == "fill_form"
    assert host.calls[0][1]["fields"] == fields
    assert host.calls[0][1]["tab_id"] == "reports"
    assert host.calls[0][1]["mode"] == "batch"
    assert host.calls[0][1].get("saved_workflow", False) == saved_workflow


def test_tab_info_returns_runtime_fields_for_workflow_references() -> None:
    data = {"tab": {"id": 42, "opener_id": 7}, "tabs": []}
    host = _FakeHost({"tabs": data})
    assert _tools(host)["browser_tabs"]("info", "last_opened") == data


def test_closing_several_pages_says_which_stayed_open() -> None:
    host = _FakeHost(
        {
            "tabs": {
                "tabs": [{"id": 3, "title": "Mine", "url": "https://m/", "active": True}],
                "closed": [{"id": 1}, {"id": 2}],
                "kept": [
                    {
                        "id": 3,
                        "title": "Mine",
                        "url": "https://m/",
                        "reason": "the user has used it",
                    }
                ],
            }
        }
    )
    output = _tools(host)["browser_tabs"]("close", tab_ids=[1, "report", 3])
    assert host.calls[0][1]["tab_ids"] == [1, "report", 3]
    assert output.splitlines()[:2] == [
        "Closed Tab 1, Tab 2.",
        "Left open Tab 3: Mine -- https://m/ -- the user has used it.",
    ]


def test_close_all_passes_the_pages_to_keep() -> None:
    host = _FakeHost({"tabs": {"tabs": [], "closed": [], "kept": []}})
    assert _tools(host)["browser_tabs"]("close_all", keep=["current"]).startswith(
        "Closed no pages."
    )
    assert host.calls[0][1]["op"] == "close_all"
    assert host.calls[0][1]["keep"] == ["current"]


@pytest.mark.parametrize(
    ("action", "kwargs"),
    [("close", {"tab_ids": []}), ("select", {"tab_ids": [1]}), ("close", {"keep": [1]})],
)
def test_page_lists_only_go_with_their_close(action: str, kwargs: dict[str, Any]) -> None:
    host = _FakeHost({})
    with pytest.raises(ValueError):
        _tools(host)["browser_tabs"](action, **kwargs)
    assert host.calls == []


def test_snapshot_reads_several_pages_at_once() -> None:
    class _Pages(_FakeHost):
        def call(
            self, action: str, args: dict[str, Any], thread_id: str, timeout: float = 30
        ) -> dict[str, Any]:
            self.calls.append((action, args, thread_id))
            if args["tab_id"] == "broken":
                raise ValueError("The page stopped responding.")
            text = f"page {args['tab_id']} " * 2000
            return {"text": text[: args["max_chars"]], "total_chars": len(text),
                    "tab": {"id": args["tab_id"], "title": "T", "url": "u"}}  # fmt: skip

    host = _Pages({})
    output = _tools(host)["browser_snapshot"](tab_ids=[1, 2, 2, "broken"])
    assert sorted(str(c[1]["tab_id"]) for c in host.calls) == ["1", "2", "broken"]
    assert all(c[1]["max_chars"] == 4000 for c in host.calls)
    pages = output.split("\n\n----\n\n")
    assert len(pages) == 3
    assert "Call browser_snapshot(tab_id=1, start=4000)" in pages[0]
    assert pages[2] == "Tab broken: couldn't read it: The page stopped responding."
    with pytest.raises(ValueError):
        _tools(host)["browser_snapshot"](start=10, tab_ids=[1])


def test_fill_form_names_the_fields_the_page_changed() -> None:
    host = _FakeHost(
        {
            "fill_form": {
                "filled": [
                    {"element": 'textbox "Name"', "value": "Ada", "changed": False},
                    {"element": 'textbox "Date"', "value": "16.11.2026", "changed": True},
                ],
                "tab": {"id": 1, "title": "Form", "url": "u"},
            }
        }
    )
    fields = [{"ref": "Name", "text": "Ada"}, {"ref": "Date", "text": "2026-11-16"}]
    lines = _tools(host)["browser_fill_form"](fields).splitlines()
    assert lines[0] == "Filled 2 fields in one page execution."
    assert lines[1].startswith('textbox "Date" now holds "16.11.2026"')
    assert 'textbox "Name"' not in "\n".join(lines)


def test_steps_are_checked_before_the_page_is_touched() -> None:
    host = _FakeHost({"steps": {"done": ["fill 2 fields", "click Save"]}})
    steps = [
        {"fill": [{"ref": "a", "text": "1"}, {"ref": "b", "text": "2"}]},
        {"click": 'button "Save"'},
        {"wait_for": "Saved"},
    ]
    assert _tools(host)["browser_steps"](steps).startswith("Did 2 steps.")
    assert host.calls[0][0] == "steps" and host.calls[0][1]["steps"] == steps
    for bad in ([], [{"click": "a", "type": "b"}], [{"click": "a", "text": "x"}], [{"fill": []}]):
        with pytest.raises(ValueError):
            _tools(host)["browser_steps"](bad)
    assert len(host.calls) == 1


def test_waiting_for_any_of_several_texts_says_which_appeared() -> None:
    host = _FakeHost({"wait_for": {"found_text": "Error", "tab": {"id": 1, "url": "u"}}})
    result = _tools(host)["browser_wait_for"](any_of=["Saved", "Error"], timeout=5)
    assert result["found"] == "Error"
    assert host.calls[0][1]["any_of"] == ["Saved", "Error"]
    with pytest.raises(ValueError):
        _tools(host)["browser_wait_for"](text="Saved", any_of=["Error"])
    with pytest.raises(ValueError):
        _tools(host)["browser_wait_for"](any_of=[])


def test_drag_takes_a_target_or_a_distance() -> None:
    host = _FakeHost({"drag": {"element": 'button "Card"', "onto": 'region "Done"'}})
    assert _tools(host)["browser_drag"]("Card", target="Done").startswith(
        'Dragged button "Card" onto region "Done".'
    )
    assert host.calls[0][1]["target"] == "Done"
    for kwargs in ({}, {"target": "Done", "by_x": 5}):
        with pytest.raises(ValueError):
            _tools(host)["browser_drag"]("Card", **kwargs)
    assert len(host.calls) == 1


def test_copy_and_paste_use_the_ai_clipboard() -> None:
    host = _FakeHost(
        {
            "copy": {"chars": 300, "preview": "x" * 200},
            "paste": {"element": 'textbox "Notes"', "formatted": True},
        }
    )
    tools = _tools(host)
    assert tools["browser_copy"]("e3").startswith(f'Copied 300 characters: "{"x" * 200}…"')
    assert tools["browser_paste"]("Notes").startswith(
        'Pasted into textbox "Notes" with its formatting.'
    )
    assert host.calls[1][1]["plain"] is False
    risks = {name: get_tool_metadata(tools[name]).risk_category for name in tools}
    assert (risks["browser_copy"], risks["browser_paste"], risks["browser_drag"]) == (
        "READ",
        "EXTERNAL",
        "EXTERNAL",
    )


def test_dropping_files_needs_the_area(tmp_path: Path) -> None:
    from coscribe.tools._workspace import WorkspaceScope

    (tmp_path / "a.pdf").write_text("x")
    host = _FakeHost({"upload": {"element": 'button "Drop here"'}})
    tools = {t.__name__: t for t in build_browser_tools("t1", host, scope=WorkspaceScope(tmp_path))}
    with pytest.raises(ValueError):
        tools["browser_file_upload"](["a.pdf"], drop=True)
    tools["browser_file_upload"](["a.pdf"], ref="Drop here", drop=True)
    assert host.calls[0][1]["drop"] is True


@pytest.mark.parametrize("saved_workflow", [False, True])
def test_fill_form_explicit_typing_mode_is_available(saved_workflow: bool) -> None:
    host = _FakeHost({"fill_form": {}})
    tools = {
        tool.__name__: tool
        for tool in build_browser_tools("t1", host, saved_workflow=saved_workflow)
    }
    result = tools["browser_fill_form"]([{"ref": "e1", "text": "value"}], mode="type")
    assert host.calls[0][1]["mode"] == "type"
    assert "sequential input" in result
    with pytest.raises(ValueError, match="mode"):
        tools["browser_fill_form"]([{"ref": "e1", "text": "value"}], mode="auto")


def test_page_steps_accept_an_explicit_fill_mode() -> None:
    host = _FakeHost({"steps": {"done": []}})
    steps = [{"fill": [{"ref": "e1", "text": "value"}], "mode": "type"}]
    _tools(host)["browser_steps"](steps)
    assert host.calls[0][1]["steps"] == steps
    with pytest.raises(ValueError, match="mode"):
        _tools(host)["browser_steps"]([{**steps[0], "mode": "auto"}])


def test_fill_form_schema_exposes_real_batch_and_sequential_modes() -> None:
    from langchain_core.utils.function_calling import convert_to_openai_tool

    schema = convert_to_openai_tool(_tools(_FakeHost({}))["browser_fill_form"])
    mode = schema["function"]["parameters"]["properties"]["mode"]
    assert mode["default"] == "batch"
    assert mode["enum"] == ["batch", "type"]
