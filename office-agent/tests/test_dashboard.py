from __future__ import annotations

import json
from pathlib import Path

import pytest

from coscribe.conversation.dashboard import (
    DashboardDataError,
    is_dashboard,
    read_dashboard_data,
    render_dashboard,
)

PAGE = b'<html><head><meta name="coscribe" content="dashboard"></head><body>x</body></html>'


def _dashboard(tmp_path: Path, manifest: object, data: dict[str, object]) -> Path:
    folder = tmp_path / "sales.dashboard"
    (folder / "data").mkdir(parents=True)
    (folder / "datasets.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name, rows in data.items():
        (folder / "data" / f"{name}.json").write_text(json.dumps(rows), encoding="utf-8")
    page = tmp_path / "sales.html"
    page.write_bytes(PAGE)
    return page


def test_only_a_page_with_the_marker_in_its_head_is_a_dashboard() -> None:
    assert is_dashboard(PAGE)
    assert is_dashboard(b"<head><META content='dashboard' name='coscribe'>")
    assert not is_dashboard(b"<html><head><title>Icons</title></head></html>")
    assert not is_dashboard(b"x" * 9000 + b'<meta name="coscribe" content="dashboard">')


def test_rows_given_as_columns_are_read_as_objects(tmp_path: Path) -> None:
    page = _dashboard(
        tmp_path,
        {"datasets": {"q3": {"source": "q3.csv"}}, "figures": {"total": {"value": 9}}},
        {"q3": {"columns": ["region", "sales"], "rows": [["East", 515], ["West", 275]]}},
    )

    data = read_dashboard_data(page)

    assert data["datasets"]["q3"]["rows"] == [
        {"region": "East", "sales": 515},
        {"region": "West", "sales": 275},
    ]
    assert data["datasets"]["q3"]["source"] == "q3.csv"
    assert data["figures"] == {"total": {"value": 9}}


def test_a_page_without_its_folder_has_no_data(tmp_path: Path) -> None:
    page = tmp_path / "sales.html"
    page.write_bytes(PAGE)

    assert read_dashboard_data(page) == {"datasets": {}, "figures": {}}


@pytest.mark.parametrize(
    ("manifest", "data", "says"),
    [
        ({"datasets": {"q3": {}}}, {"q3": {"rows": [1]}}, "neither a list of rows"),
        ({"datasets": {"../x": {}}}, {}, "plain id"),
        ([], {}, "not an object"),
    ],
)
def test_data_that_cannot_be_read_says_why(
    tmp_path: Path, manifest: object, data: dict[str, object], says: str
) -> None:
    page = _dashboard(tmp_path, manifest, data)

    with pytest.raises(DashboardDataError, match=says):
        read_dashboard_data(page)


def test_the_data_goes_in_first_and_cannot_close_its_script_early(tmp_path: Path) -> None:
    page = _dashboard(
        tmp_path,
        {"datasets": {"notes": {}}},
        {"notes": [{"text": "</script><script>alert(1)</script>"}]},
    )

    body = render_dashboard(page, PAGE).decode("utf-8")

    assert body.index("window.coscribe=") < body.index('<meta name="coscribe"')
    assert "</script><script>alert" not in body
    assert "<\\/script>" in body


def test_a_page_whose_data_is_broken_still_opens_and_is_told_why(tmp_path: Path) -> None:
    page = _dashboard(tmp_path, {"datasets": {"q3": {}}}, {})
    (tmp_path / "sales.dashboard" / "data" / "q3.json").write_text("{", encoding="utf-8")

    body = render_dashboard(page, PAGE).decode("utf-8")

    assert '"error": "data/q3.json is not valid JSON' in body


def test_d3_is_put_in_only_where_the_page_asks_for_it(tmp_path: Path) -> None:
    page = _dashboard(tmp_path, {"datasets": {}}, {})
    asks = PAGE.replace(b"</head>", b'<script data-coscribe-lib="d3"></script></head>')

    assert b"scaleLinear" in render_dashboard(page, asks)
    assert b"scaleLinear" not in render_dashboard(page, PAGE)
