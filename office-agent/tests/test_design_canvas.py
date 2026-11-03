from __future__ import annotations

import json
from pathlib import Path

import pytest

from coscribe.conversation.design_canvas import (
    BOARD_INSPECTOR,
    BOARD_LINKS,
    CanvasError,
    in_canvas_folder,
    in_scheme,
    place_on_canvas,
    read_canvas,
    variables_style,
)


def _canvas(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "poster.design.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_boards_without_a_place_are_laid_out_left_to_right(tmp_path: Path) -> None:
    path = _canvas(
        tmp_path,
        {"boards": [{"id": "a", "file": "a.html"}, {"id": "b", "file": "b.html", "width": 390}]},
    )

    boards = read_canvas(path)["boards"]

    assert [(b["x"], b["y"], b["width"], b["height"]) for b in boards] == [
        (0, 0, 1280, 800),
        (1360, 0, 390, 800),
    ]
    assert boards[0]["title"] == "a"


@pytest.mark.parametrize(
    ("data", "says"),
    [
        ({"boards": [{"id": "a", "file": "../x.html"}]}, "needs `file`"),
        ({"boards": [{"id": "a b", "file": "a.html"}]}, "plain id"),
        ({"boards": [{"id": "a", "file": "a.html"}, {"id": "a", "file": "b.html"}]}, "same id"),
        ({"pages": []}, "`boards` list"),
    ],
)
def test_a_canvas_that_cannot_be_drawn_says_why(tmp_path: Path, data: object, says: str) -> None:
    with pytest.raises(CanvasError, match=says):
        read_canvas(_canvas(tmp_path, data))


def test_placing_moves_only_the_named_boards_and_keeps_the_rest_of_the_file(
    tmp_path: Path,
) -> None:
    path = _canvas(
        tmp_path,
        {
            "boards": [
                {"id": "a", "file": "a.html", "theme": "dark"},
                {"id": "b", "file": "b.html"},
            ],
            "made_by": "coscribe",
        },
    )

    place_on_canvas(
        path,
        {"a": {"x": 40, "y": -60, "width": 10}, "gone": {"x": 1}},
        [{"text": "Ask about colours", "x": 5}, {"text": "  "}],
    )

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["made_by"] == "coscribe" and saved["boards"][0]["theme"] == "dark"
    assert (saved["boards"][0]["x"], saved["boards"][0]["y"], saved["boards"][0]["width"]) == (
        40,
        -60,
        40,
    )
    assert "x" not in saved["boards"][1]
    assert [n["text"] for n in saved["notes"]] == ["Ask about colours"]


def test_an_artboards_page_belongs_to_its_canvas(tmp_path: Path) -> None:
    _canvas(tmp_path, {"boards": []})
    (tmp_path / "poster.design").mkdir()
    (tmp_path / "poster.design" / "a.html").write_text("<p>", encoding="utf-8")
    (tmp_path / "loose.design").mkdir()
    (tmp_path / "loose.design" / "b.html").write_text("<p>", encoding="utf-8")

    assert in_canvas_folder(tmp_path / "poster.design" / "a.html")
    assert not in_canvas_folder(tmp_path / "loose.design" / "b.html")


def test_variables_that_could_break_out_of_a_style_are_dropped_and_the_rest_set_every_root(
    tmp_path: Path,
) -> None:
    path = _canvas(
        tmp_path,
        {
            "boards": [],
            "variables": [
                {"name": "--brand", "value": "#2557d6", "label": "Brand"},
                {"name": "--font", "value": " 'Segoe UI', sans-serif "},
                {"name": "--evil", "value": "red}</style><script>"},
                {"name": "--sly", "value": "red /* "},
                {"name": "brand", "value": "red"},
                {"name": "--brand", "value": "#000"},
            ],
        },
    )

    canvas = read_canvas(path)

    assert [(v["name"], v["value"], v["label"]) for v in canvas["variables"]] == [
        ("--brand", "#000", "brand"),
        ("--font", "'Segoe UI', sans-serif", "font"),
    ]
    assert variables_style(canvas) == (
        b"<style data-coscribe-variables>:root{--brand:#000;--font:'Segoe UI', sans-serif}</style>"
    )
    assert variables_style(read_canvas(_canvas(tmp_path, {"boards": []}))) == b""


def test_placing_sets_only_declared_variables_to_safe_values(tmp_path: Path) -> None:
    path = _canvas(tmp_path, {"boards": [], "variables": [{"name": "--brand", "value": "#2557d6"}]})

    place_on_canvas(path, {}, None, {"--brand": "#e0457b", "--new": "red"})
    place_on_canvas(path, {}, None, {"--brand": "x;}"})

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["variables"] == [{"name": "--brand", "value": "#e0457b"}]


def test_a_page_in_a_scheme_has_its_colour_scheme_queries_answered_and_its_theme_set() -> None:
    page = (
        b"<style>@media (prefers-color-scheme: dark){body{background:#111}}"
        b"@media (PREFERS-COLOR-SCHEME:light){body{background:#fff}}</style>"
        b"<script>matchMedia('(prefers-color-scheme: dark)')</script>"
    )

    dark = in_scheme(page, "dark")

    assert b"prefers-color-scheme" not in dark.lower()
    assert dark.count(b"min-width:0px") == 2 and dark.count(b"max-width:-1px") == 1
    assert dark.startswith(b"<style>:root{color-scheme:dark}</style><script>")
    assert b"setAttribute('data-theme','dark')" in dark
    assert in_scheme(page, "light").count(b"min-width:0px") == 1
    assert in_scheme(page, "sepia") == page


def test_an_artboard_is_served_with_its_links_to_other_artboards_handed_to_the_panel(
    tmp_path: Path,
) -> None:
    from coscribe.conversation import served_page

    _canvas(tmp_path, {"boards": [{"id": "a", "file": "a.html"}]})
    (tmp_path / "poster.design").mkdir()
    page = tmp_path / "poster.design" / "a.html"
    loose = tmp_path / "loose.html"

    served = served_page(page, b"<html><head></head><a href='b.html'>b</a></html>")

    assert served.index(BOARD_LINKS) < served.index(b"</head>")
    assert served.index(BOARD_INSPECTOR) < served.index(b"</head>")
    assert BOARD_LINKS not in served_page(loose, b"<a href='b.html'>b</a>")
    assert b"</script" not in BOARD_INSPECTOR[len(b"<script>") : -len(b"</script>")].lower()


def test_a_part_is_filled_into_each_page_that_places_it_and_a_missing_one_is_marked(
    tmp_path: Path,
) -> None:
    from coscribe.conversation import served_page

    _canvas(tmp_path, {"boards": [{"id": "a", "file": "a.html"}]})
    folder = tmp_path / "poster.design"
    folder.mkdir()
    (folder / "tabs.part.html").write_bytes(b"<nav class='tabs'>Home</nav>")
    page = folder / "a.html"
    source = (
        b"<html><head></head><body><h1>Hi</h1><coscribe-part name='tabs'></coscribe-part>"
        b'<coscribe-part name="gone"></coscribe-part></body></html>'
    )

    served = served_page(page, source)

    assert (
        b'<coscribe-part name="tabs" style="display:contents"><nav class=\'tabs\'>Home</nav>'
        b"</coscribe-part>"
    ) in served
    assert b"Missing part: gone" in served
    # Only an artboard's page is filled; a page of its own is served as written.
    loose = tmp_path / "loose.html"
    assert b"<nav" not in served_page(loose, source)


def test_a_picture_file_of_the_canvas_folder_is_filled_in_and_nothing_outside_it(
    tmp_path: Path,
) -> None:
    import base64

    from coscribe.conversation import served_page

    _canvas(tmp_path, {"boards": [{"id": "a", "file": "a.html"}]})
    folder = tmp_path / "poster.design"
    (folder / "brand").mkdir(parents=True)
    logo = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    (folder / "logo.svg").write_bytes(logo)
    (folder / "brand" / "mark.png").write_bytes(b"\x89PNG fake")
    (tmp_path / "secret.png").write_bytes(b"\x89PNG secret")
    (folder / "tabs.part.html").write_bytes(b"<img alt='p' src='logo.svg'>")
    source = (
        b'<body><img src="logo.svg" alt="Logo"><svg><image href="brand/mark.png"/></svg>'
        b'<img src="../secret.png"><img src="gone.png"><img src="https://example.com/x.png">'
        b"<coscribe-part name='tabs'></coscribe-part></body>"
    )

    served = served_page(folder / "a.html", source)

    data = b"data:image/svg+xml;base64," + base64.b64encode(logo)
    assert served.count(data) == 2  # the page's and the part's
    assert b'href="data:image/png;base64,' + base64.b64encode(b"\x89PNG fake") in served
    for left in (b'src="../secret.png"', b'src="gone.png"', b'src="https://example.com/x.png"'):
        assert left in served
