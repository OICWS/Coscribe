"""The deterministic parts of the Doc routing evaluation: what the agent left is classified, and a
Doc is read as the app reads it."""

from __future__ import annotations

from pathlib import Path

from evals.doc_route import BRIEFS, Brief, classify, doc_report, judge

GOOD = """---
coscribe: doc
---

# Plan

Ships 15 March for 4,800.

> [!NOTE]
> Budget is not final.

```chart
bar Sales
| q | n |
| --- | --- |
| Q1 | 3 |
```
"""


def test_the_briefs_cover_the_three_routes() -> None:
    assert sorted({b.expect for b in BRIEFS}) == ["chat", "doc", "docx"]
    assert len({b.name for b in BRIEFS}) == len(BRIEFS) == 15


def test_what_the_agent_left_is_classified_and_an_input_left_alone_is_not_counted(
    tmp_path: Path,
) -> None:
    (tmp_path / "in.docx").write_bytes(b"input")
    (tmp_path / "plain.md").write_text("# Notes\n", encoding="utf-8")
    assert classify(tmp_path, {"in.docx": b"input"})["got"] == "plain_md"

    (tmp_path / "plan.md").write_text(GOOD, encoding="utf-8")
    found = classify(tmp_path, {"in.docx": b"input"})
    assert (found["got"], found["docs"], found["plain_md"]) == ("doc", ["plan.md"], ["plain.md"])

    (tmp_path / "in.docx").write_bytes(b"changed")
    assert classify(tmp_path, {"in.docx": b"input"})["docx"] == ["in.docx"]
    assert classify(tmp_path / "nothing-here", {})["got"] == "none"


def test_a_doc_is_read_for_raw_blocks_bad_charts_and_missing_facts() -> None:
    good = doc_report(GOOD, ("15 March", "4,800"))
    assert good["blocks"] == {"heading": 1, "paragraph": 1, "callout": 1, "chart": 1}
    assert not (good["raw_blocks"] or good["bad_charts"] or good["missing_facts"])

    broken = GOOD.replace("| Q1 | 3 |", "| Q1 | lots |") + "\n<div>x</div>\n"
    report = doc_report(broken, ("15 March", "June"))
    assert report["raw_blocks"] == ["html"] and len(report["bad_charts"]) == 1
    assert report["missing_facts"] == ["June"]


def test_a_route_is_right_only_when_it_is_the_expected_one(tmp_path: Path) -> None:
    (tmp_path / "plan.md").write_text(GOOD, encoding="utf-8")
    brief = Brief("x", "write", "doc", ("15 March",))

    right = judge(brief, tmp_path, {}, {"load_skill": 1})
    wrong = judge(Brief("y", "write", "docx"), tmp_path, {}, {})

    assert right["route_ok"] and right["skill_loaded"] and right["valid"]
    assert not wrong["route_ok"] and not wrong["skill_loaded"]


def test_an_answer_in_chat_is_the_right_route_when_no_file_was_left(tmp_path: Path) -> None:
    chat = Brief("q", "what is margin?", "chat")

    assert judge(chat, tmp_path, {}, {})["route_ok"]
    (tmp_path / "plan.md").write_text(GOOD, encoding="utf-8")
    assert not judge(chat, tmp_path, {}, {})["route_ok"]
