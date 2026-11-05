from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from coscribe.conversation import page_shot
from coscribe.conversation.page_tools import build_page_tools
from coscribe.runtime_lg import tool_result_value
from coscribe.runtime_lg.messages import pictures_as_user_message
from coscribe.tools import WorkspaceScope

_PICTURE = {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}


def test_a_tool_results_pictures_move_into_one_user_message_after_that_steps_results() -> None:
    calls = [{"name": "look_at_page", "args": {}, "id": "a"}, {"name": "x", "args": {}, "id": "b"}]
    messages = [
        HumanMessage(content="make a poster"),
        AIMessage(content="", tool_calls=calls),
        ToolMessage(content=[{"type": "text", "text": "{}"}, _PICTURE], tool_call_id="a"),
        ToolMessage(content="done", tool_call_id="b"),
        AIMessage(content="It looks right."),
    ]

    moved, changed = pictures_as_user_message(messages)

    assert changed and len(moved) == 6
    assert moved[2].content == [{"type": "text", "text": "{}"}] and moved[3].content == "done"
    assert isinstance(moved[4], HumanMessage) and moved[4].content[1] == _PICTURE
    assert messages[2].content[1] == _PICTURE
    assert pictures_as_user_message(messages[:2]) == (messages[:2], False)


def test_the_tab_and_the_history_get_a_pictures_text_and_how_many_there_were() -> None:
    content = [{"type": "text", "text": '{"path": "a.html"}'}, _PICTURE, _PICTURE]

    assert tool_result_value(content) == {"path": "a.html", "pictures": 2}
    assert tool_result_value('{"ok": true}') == {"ok": True}


def test_the_browser_is_edge_or_chrome_where_windows_installs_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    edge = tmp_path / "Microsoft" / "Edge" / "Application" / "msedge.exe"
    edge.parent.mkdir(parents=True)
    edge.write_bytes(b"")
    monkeypatch.delenv("COSCRIBE_PAGE_BROWSER", raising=False)
    monkeypatch.setattr(page_shot.sys, "platform", "win32")
    for name in ("ProgramFiles(x86)", "LocalAppData"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ProgramFiles", str(tmp_path))

    assert page_shot.find_browser() == str(edge)

    monkeypatch.setenv("COSCRIBE_PAGE_BROWSER", str(tmp_path / "missing.exe"))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "nowhere"))
    assert page_shot.find_browser() is None


def _local_chromium() -> str | None:
    found = sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))
    return os.environ.get("COSCRIBE_PAGE_BROWSER") or (str(found[-1]) if found else None)


needs_browser = pytest.mark.skipif(
    _local_chromium() is None and page_shot.find_browser() is None,
    reason="no Chromium-family browser here; test_windows_real.py draws with Edge",
)


@needs_browser
def test_look_at_page_draws_each_artboard_with_its_canvas_and_reports_what_is_wrong(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if (chromium := _local_chromium()) is not None:
        monkeypatch.setenv("COSCRIBE_PAGE_BROWSER", chromium)
    (tmp_path / "p.design").mkdir()
    poster = (
        "<html><head><style>html,body{margin:0;width:100%;height:100%}"
        "h1{color:var(--brand);font:40px sans-serif;margin:10px}"
        ".tag{position:absolute;top:14px;left:14px;font:30px sans-serif}"
        ".end{position:absolute;left:350px;top:200px;font:30px sans-serif}</style></head>"
        "<body><h1>Safety Day</h1><div class='tag'>Overlap</div><div class='end'>Cut off</div>"
        "<img src='https://example.com/a.png'></body></html>"
    )
    (tmp_path / "p.design" / "poster.html").write_text(poster, encoding="utf-8")
    (tmp_path / "p.design" / "fine.html").write_text("<p>ok</p>", encoding="utf-8")
    canvas = {
        "boards": [
            {"id": "poster", "file": "poster.html", "width": 400, "height": 260},
            {"id": "fine", "file": "fine.html", "width": 300, "height": 200},
            {"id": "gone", "file": "gone.html"},
        ],
        "variables": [{"name": "--brand", "value": "#ff0000"}],
    }
    (tmp_path / "p.design.json").write_text(json.dumps(canvas), encoding="utf-8")
    (look_at_page,) = build_page_tools(lambda: WorkspaceScope(tmp_path))

    result = look_at_page("p.design.json")

    summary = json.loads(result[0]["text"])
    poster_page, fine_page, gone_page = summary["pages"]
    assert poster_page["board"] == "poster" and poster_page["size"] == "400x260"
    assert poster_page["text_overlapping"] == [["Safety Day", "Overlap"]]
    assert poster_page["text_past_edge"] == ["Cut off"]
    assert any("blocked" in e for e in poster_page["errors"])
    assert fine_page["text_overlapping"] == [] and not fine_page["errors"]
    # A board narrower than any headless window is still laid out and measured at its own width.
    assert fine_page["wider_than_board"] is False and fine_page["content_width"] == 300
    assert gone_page == {"board": "gone", "problem": "gone.html does not exist"}
    assert [b["type"] for b in result[1:]] == ["image_url", "image_url"]

    from PIL import Image

    png = base64.b64decode(result[1]["image_url"]["url"].split(",", 1)[1])
    image = Image.open(io.BytesIO(png)).convert("RGB")
    assert image.size == (400, 260)
    raw = image.tobytes()
    pixels = zip(raw[0::3], raw[1::3], raw[2::3], strict=True)
    # The heading takes the canvas's variable, as the app draws it.
    assert any(r > 200 and g < 80 and b < 80 for r, g, b in pixels)

    alone = look_at_page("p.design.json", board="fine")
    assert [p["board"] for p in json.loads(alone[0]["text"])["pages"]] == ["fine"]
    with pytest.raises(ValueError, match="no artboard"):
        look_at_page("p.design.json", board="nope")
    with pytest.raises(ValueError, match="light"):
        look_at_page("p.design.json", scheme="sepia")


@needs_browser
def test_an_artboard_exports_as_a_png_at_twice_its_size_and_a_square_one_as_an_icon(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PIL import Image

    from coscribe.conversation import NotSquare, PageShotError, export_board

    if (chromium := _local_chromium()) is not None:
        monkeypatch.setenv("COSCRIBE_PAGE_BROWSER", chromium)
    (tmp_path / "logo.design").mkdir()
    canvas = {
        "boards": [
            {"id": "wide", "file": "wide.html", "width": 300, "height": 200},
            {"id": "mark", "file": "mark.html", "width": 128, "height": 128},
        ],
        "variables": [{"name": "--brand", "value": "#ff0000"}],
    }
    (tmp_path / "logo.design.json").write_text(json.dumps(canvas), encoding="utf-8")
    page = "<html><head><style>body{margin:0;background:var(--brand)}</style></head></html>"
    for name in ("wide", "mark"):
        (tmp_path / "logo.design" / f"{name}.html").write_text(page, encoding="utf-8")
    wide, mark = tmp_path / "logo.design" / "wide.html", tmp_path / "logo.design" / "mark.html"

    with Image.open(io.BytesIO(export_board(wide, "png"))) as png:
        # Drawn as the app serves it: the canvas's variable fills the page.
        assert png.size == (600, 400)
        assert png.convert("RGB").getpixel((300, 200)) == (255, 0, 0)
    with Image.open(io.BytesIO(export_board(mark, "ico"))) as ico:
        assert ico.format == "ICO"
        assert {(16, 16), (32, 32), (256, 256)} <= set(ico.info["sizes"])
    with pytest.raises(NotSquare):
        export_board(wide, "ico")
    loose = tmp_path / "loose.html"
    loose.write_text(page, encoding="utf-8")
    with pytest.raises(PageShotError, match="artboard"):
        export_board(loose, "png")


def test_a_canvas_is_told_when_no_artboard_places_the_conversations_logo(tmp_path: Path) -> None:
    from coscribe.conversation.page_tools import _logo_note
    from coscribe.tools import DesignSystemStore

    store = DesignSystemStore(tmp_path / "state")
    made = store.create("Acme")
    logo = store.add_asset(made["id"], b'<svg xmlns="http://www.w3.org/2000/svg"/>', "logo.svg")
    assert logo is not None
    store.update_asset(made["id"], logo["id"], {"kind": "logo", "note": "in the header"})
    canvas = tmp_path / "p.design.json"
    canvas.write_text(
        json.dumps({"boards": [{"id": "a", "file": "a.html"}, {"id": "b", "file": "b.html"}]}),
        encoding="utf-8",
    )
    (tmp_path / "p.design").mkdir()
    (tmp_path / "p.design" / "a.html").write_text("<p>Hi</p>", encoding="utf-8")
    (tmp_path / "p.design" / "b.html").write_text("<img src='mark.svg'>", encoding="utf-8")
    assert _logo_note(canvas, tmp_path / "state", "t1") is None  # no system chosen
    store.choose_for_thread("t1", made["id"])

    note = _logo_note(canvas, tmp_path / "state", "t1")
    (tmp_path / "p.design" / "mark.svg").write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"/>')

    assert note is not None and "no artboard places" in note and "(in the header)" in note
    assert _logo_note(canvas, tmp_path / "state", "t1") is None
