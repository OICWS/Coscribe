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
    page = "<style>:root{--gap:8px} p{color:var(--brand);margin:var(--gap);top:var(--lost)}</style>"
    (tmp_path / "x.design" / "a.html").write_text(page, encoding="utf-8")

    report = canvas_report(canvas)

    assert [b["exists"] for b in report["boards"]] == [True, False]
    assert report["variables"] == ["--brand", "--font"]
    assert report["variables_used"] == ["--brand"]
    assert report["undeclared"] == ["--lost"]


def test_a_broken_canvas_is_reported_not_raised(tmp_path: Path) -> None:
    canvas = tmp_path / "x.design.json"
    canvas.write_text("{", encoding="utf-8")

    assert canvas_report(canvas)["canvas_error"] == "x.design.json is not valid JSON"


def test_the_briefs_are_six_with_both_starts_and_a_chinese_one() -> None:
    assert len(BRIEFS) == 6 and len({b.name for b in BRIEFS}) == 6
    assert {b.from_tile for b in BRIEFS} == {True, False}
    assert any("设计" in b.text for b in BRIEFS)
