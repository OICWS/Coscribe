from __future__ import annotations

import json
from pathlib import Path

from evals.dashboard_route import BRIEFS, figures_found, page_report

PAGE = """<html><head><meta name="coscribe" content="dashboard"></head><body>
<h1>Sales</h1><span data-figure="total">—</span><span data-figure="growth">—</span>
<div data-source="q3"></div><div data-source="q4"></div><p>Up 1,520 on 2025 and 12.5%.</p>
<script>const x = 9999;</script></body></html>"""


def _dashboard(tmp_path: Path) -> Path:
    (tmp_path / "s.dashboard" / "data").mkdir(parents=True)
    manifest = {"datasets": {"q3": {"source": "q3.csv"}}, "figures": {"total": {"value": 0.85}}}
    (tmp_path / "s.dashboard" / "datasets.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "s.dashboard" / "data" / "q3.json").write_text('[{"a": 1}]', encoding="utf-8")
    page = tmp_path / "s.html"
    page.write_text(PAGE, encoding="utf-8")
    return page


def test_a_page_report_names_unknown_bindings_and_figures_typed_into_the_page(
    tmp_path: Path,
) -> None:
    report = page_report(_dashboard(tmp_path))

    assert report["datasets"] == {"q3": 1} and report["figures"] == {"total": 0.85}
    assert report["unknown_names"] == ["figure:growth", "source:q4"]
    # Numbers in the page's text count; a script's do not, and a year is not a figure.
    assert report["typed_numbers"] == ["1,520", "12.5%"]
    assert report["sources_named"] and not report["data_error"]


def test_an_expected_number_is_found_as_it_is_or_as_a_rate() -> None:
    assert figures_found({"rate": 0.85, "n": 40}, ((85, 0.5), (40, 0), (7, 0))) == [
        True,
        True,
        False,
    ]


def test_every_brief_has_its_data_file() -> None:
    for brief in BRIEFS:
        assert brief.inputs
        assert all(make() for make in brief.inputs.values())
