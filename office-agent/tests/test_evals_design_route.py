from __future__ import annotations

import json
from pathlib import Path

from evals.design_route import BRIEFS, canvas_report


def test_a_canvas_report_names_missing_pages_and_variables_nobody_declared(
    tmp_path: Path,
) -> None:
    boards = [{"id": "a", "file": "a.html"}, {"id": "b", "file": "b.html"}]
    variables = [{"name": "--brand", "value": "#123"}, {"name": "--font", "value": "serif"}]
    canvas = tmp_path / "x.design.json"
    canvas.write_text(json.dumps({"boards": boards, "variables": variables}), encoding="utf-8")
    (tmp_path / "x.design").mkdir()
    page = (
        "<style>:root{--gap:8px} p{color:var(--brand);margin:var(--gap);top:var(--lost)}</style>"
        "<a href='b.html'>Next</a><a class='x' href=\"gone.html#top\"><button>Go</button></a>"
    )
    (tmp_path / "x.design" / "a.html").write_text(page, encoding="utf-8")

    report = canvas_report(canvas)

    assert [b["exists"] for b in report["boards"]] == [True, False]
    assert report["variables"] == ["--brand", "--font"]
    assert report["variables_used"] == ["--brand"]
    assert report["undeclared"] == ["--lost"]
    assert (report["links"], report["broken_links"], report["buttons_in_links"]) == (
        1,
        ["gone.html"],
        1,
    )


def test_a_broken_canvas_is_reported_not_raised(tmp_path: Path) -> None:
    canvas = tmp_path / "x.design.json"
    canvas.write_text("{", encoding="utf-8")

    assert canvas_report(canvas)["canvas_error"] == "x.design.json is not valid JSON"


def test_the_briefs_have_both_starts_a_chinese_one_and_a_linked_prototype() -> None:
    assert len({b.name for b in BRIEFS}) == len(BRIEFS) == 7
    assert any(b.linked for b in BRIEFS)
    assert {b.from_tile for b in BRIEFS} == {True, False}
    assert any("设计" in b.text for b in BRIEFS)
