"""An element edited from the canvas's properties panel is written into the artboard's own source,
touching nothing else, and coscribe is told once at its next turn."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coscribe.conversation import (
    BoardEditError,
    edit_board_element,
    remember_board_edit,
    user_edits,
)
from coscribe.conversation.board_edits import board_edits_since_told
from coscribe.conversation.user_edits import design_edits_note
from coscribe.tools import WorkspaceScope

PAGE = """<!doctype html>
<html><head>
<style>:root { --brand: #2557d6; } h1 { font-size: 40px; }</style>
</head>
<body>
  <script>var x = 1;</script>
  <div class="row" style="gap: 8px">
    <h1>Hello &amp; welcome</h1>
    <img src="data:image/png;base64,AA">
    <p>World <b>bold</b></p>
  </div>
</body></html>
"""


def _page(tmp_path: Path, source: str = PAGE) -> Path:
    (tmp_path / "ui.design").mkdir()
    (tmp_path / "ui.design.json").write_text(
        json.dumps({"boards": [{"id": "home", "file": "home.html"}]}), encoding="utf-8"
    )
    page = tmp_path / "ui.design" / "home.html"
    page.write_text(source, encoding="utf-8")
    return page


def test_a_style_goes_into_the_elements_own_attribute_and_nothing_else_changes(
    tmp_path: Path,
) -> None:
    page = _page(tmp_path)
    # The body's script counts as its first child, as in the browser's DOM.
    said = edit_board_element(
        page, "1.0", "h1", style={"font-size": "28px", "color": "var(--brand)"}
    )
    after = page.read_text(encoding="utf-8")
    assert '<h1 style="font-size: 28px; color: var(--brand)">Hello &amp; welcome</h1>' in after
    assert after.replace(' style="font-size: 28px; color: var(--brand)"', "") == PAGE
    assert said == "<h1> 'Hello & welcome': font-size 28px, color var(--brand)"

    edit_board_element(page, "1", "div", style={"gap": "16px", "padding": "12px"})
    assert '<div class="row" style="gap: 16px; padding: 12px">' in page.read_text(encoding="utf-8")
    edit_board_element(page, "1", "div", style={"gap": ""})
    assert '<div class="row" style="padding: 12px">' in page.read_text(encoding="utf-8")


def test_text_is_replaced_only_in_an_element_that_holds_text_alone(tmp_path: Path) -> None:
    page = _page(tmp_path)
    edit_board_element(page, "1.0", "h1", text="Hi <there>", text_before="Hello & welcome")
    assert "<h1>Hi &lt;there&gt;</h1>" in page.read_text(encoding="utf-8")
    # A void element before the paragraph still counts as one child.
    with pytest.raises(BoardEditError, match="holds text alone"):
        edit_board_element(page, "1.2", "p", text="x")


def test_an_edit_is_refused_when_the_page_no_longer_matches_or_the_value_could_break_out(
    tmp_path: Path,
) -> None:
    page = _page(tmp_path)
    with pytest.raises(BoardEditError, match="pick it again"):
        edit_board_element(page, "1.0", "p", style={"color": "red"})
    with pytest.raises(BoardEditError, match="pick it again"):
        edit_board_element(page, "1.0", "h1", text="x", text_before="Something else")
    for bad_name in ("back ground", "color;x", 'x"y', "Color"):
        with pytest.raises(BoardEditError, match="not a CSS property name"):
            edit_board_element(page, "1.0", "h1", style={bad_name: "red"})
    for bad in ('red" onclick="x', "red; display: none", "red</style>"):
        with pytest.raises(BoardEditError, match="not a value"):
            edit_board_element(page, "1.0", "h1", style={"color": bad})
    assert page.read_text(encoding="utf-8") == PAGE

    loose = tmp_path / "loose.html"
    loose.write_text("<body><p>x</p></body>", encoding="utf-8")
    with pytest.raises(BoardEditError, match="artboard"):
        edit_board_element(loose, "0", "p", style={"color": "red"})


def test_coscribe_is_told_once_which_design_and_what_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page, state, scope = _page(tmp_path), tmp_path / "state", WorkspaceScope(tmp_path)
    entries = [{"path": "ui.design/home.html", "exists": True}]
    monkeypatch.setattr(
        user_edits, "summarize_activity", lambda *_: {"outputs": entries, "references": []}
    )
    assert design_edits_note([], {}, scope, state) == ""

    said = edit_board_element(page, "1.0", "h1", style={"font-size": "28px"})
    remember_board_edit(page, said, state)
    note = design_edits_note([], {}, scope, state)

    assert note.startswith("[The user edited the design ui.design.json in the app since your last")
    assert "home.html <h1> 'Hello & welcome': font-size 28px" in note
    assert note.endswith("]\n\n")
    assert design_edits_note([], {}, scope, state) == ""
    assert board_edits_since_told(tmp_path / "ui.design.json", state) == []


def test_a_page_without_a_body_tag_counts_as_the_browser_does(tmp_path: Path) -> None:
    # The browser keeps the style in the head and makes a body at the first <div>.
    page = _page(
        tmp_path, "<style>p{margin:0}</style><div><p>a</p></div><script>1</script><p>b</p>"
    )
    edit_board_element(page, "2", "p", text="c", text_before="b")
    edit_board_element(page, "0.0", "p", style={"color": "red"})
    assert page.read_text(encoding="utf-8") == (
        '<style>p{margin:0}</style><div><p style="color: red">a</p></div><script>1</script><p>c</p>'
    )


def test_comments_quoted_angles_and_script_text_do_not_count_as_elements(tmp_path: Path) -> None:
    source = (
        "<body><!-- <div>not one</div> --><script>var s = '<p>x</p>';</script>"
        '<a title="a > b" href="#">link</a><p>target</p></body>'
    )
    page = _page(tmp_path, source)
    edit_board_element(page, "2", "p", style={"color": "red"})
    assert page.read_text(encoding="utf-8").endswith('<p style="color: red">target</p></body>')


def test_undo_and_redo_step_through_the_panels_edits_and_keep_coscribe_told_rightly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.conversation import (
        NothingToUndo,
        PageWrittenSince,
        keep_for_undo,
        redo_board_edit,
        steps_left,
        undo_board_edit,
    )

    page, state, scope = _page(tmp_path), tmp_path / "state", WorkspaceScope(tmp_path)
    entries = [{"path": "ui.design.json", "exists": True}]
    monkeypatch.setattr(
        user_edits, "summarize_activity", lambda *_: {"outputs": entries, "references": []}
    )

    def edit(**change: object) -> None:
        before = page.read_text(encoding="utf-8")
        said = edit_board_element(page, "1.0", "h1", **change)  # type: ignore[arg-type]
        remember_board_edit(page, said, state)
        keep_for_undo(page, before, said, state)

    assert steps_left(page, state) == {"undo": 0, "redo": 0}
    edit(style={"color": "red"})
    after_first = page.read_text(encoding="utf-8")
    edit(style={"font-size": "28px"})
    after_second = page.read_text(encoding="utf-8")
    assert steps_left(page, state) == {"undo": 2, "redo": 0}

    assert undo_board_edit(page, state) == {"undo": 1, "redo": 1}
    assert page.read_text(encoding="utf-8") == after_first
    # The undone edit was never told, so the note has only the first.
    note = design_edits_note([], {}, scope, state)
    assert "color red" in note and "font-size" not in note

    # Redo writes the edit back; told since its undo, so it is said again.
    assert redo_board_edit(page, state) == {"undo": 2, "redo": 0}
    assert page.read_text(encoding="utf-8") == after_second
    assert "font-size 28px" in design_edits_note([], {}, scope, state)
    with pytest.raises(NothingToUndo):
        redo_board_edit(page, state)

    # Told already: undoing now is reported as undone, and the steps survive a reload.
    assert undo_board_edit(page, state) == {"undo": 1, "redo": 1}
    assert undo_board_edit(page, state) == {"undo": 0, "redo": 2}
    assert page.read_text(encoding="utf-8") == PAGE
    assert steps_left(page, state) == {"undo": 0, "redo": 2}
    assert "undid <h1> 'Hello & welcome': font-size 28px" in design_edits_note([], {}, scope, state)
    with pytest.raises(NothingToUndo):
        undo_board_edit(page, state)

    # A new edit drops what there was to redo.
    edit(style={"color": "blue"})
    assert steps_left(page, state) == {"undo": 1, "redo": 0}

    # A page coscribe wrote after the edit is not put back over its work.
    page.write_text(PAGE.replace("World", "Earth"), encoding="utf-8")
    assert steps_left(page, state) == {"undo": 0, "redo": 0}
    with pytest.raises(PageWrittenSince):
        undo_board_edit(page, state)
    assert "Earth" in page.read_text(encoding="utf-8")
    with pytest.raises(NothingToUndo):
        undo_board_edit(page, state)
