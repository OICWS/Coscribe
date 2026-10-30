from __future__ import annotations

import json
from pathlib import Path

import pytest

from coscribe.conversation.design_canvas import (
    CanvasError,
    in_canvas_folder,
    place_on_canvas,
    read_canvas,
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
