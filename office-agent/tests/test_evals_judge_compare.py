"""The blind judge's bookkeeping and the two-run comparison (`evals/judge.py`, `evals/compare.py`).
The judge model itself is replaced by a function that answers; nothing here calls a vendor."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from evals import compare, judge

TASK = "01-q3-review"


def test_labels_are_a_random_permutation_of_the_first_letters() -> None:
    labels = judge.assign_labels(3, random.Random(1))

    assert sorted(labels) == ["Deck P", "Deck Q", "Deck R"]
    assert judge.assign_labels(3, random.Random(1)) == labels
    assert any(judge.assign_labels(3, random.Random(s)) != labels for s in range(2, 20))


def _answer(**scores: float) -> str:
    deck = {"design": 4, "content": 4, "coherence": 4, "defects": []}
    return json.dumps({"decks": {"P": {**deck, **scores}, "Q": deck}, "ranking": ["P", "Q"]})


def test_an_answer_that_names_decks_by_letter_is_matched_to_the_labels() -> None:
    parsed = judge.parse_answer(_answer(design=2.5), ["Deck Q", "Deck P"])

    assert parsed["decks"]["Deck P"]["design"] == 2.5
    assert parsed["ranking"] == ["Deck P", "Deck Q"]


@pytest.mark.parametrize("bad", [0, 6, "high", None])
def test_a_score_outside_one_to_five_is_refused(bad: object) -> None:
    with pytest.raises(ValueError, match="not a score"):
        judge.parse_answer(_answer(design=bad), ["Deck P", "Deck Q"])  # type: ignore[arg-type]


def test_a_missing_deck_is_refused() -> None:
    with pytest.raises(KeyError):
        judge.parse_answer(_answer(), ["Deck P", "Deck Q", "Deck R"])


def test_the_request_lists_decks_in_label_order_with_every_page(tmp_path: Path) -> None:
    pages = {"Deck Q": [tmp_path / "q1.png"], "Deck P": [tmp_path / "p1.png", tmp_path / "p2.png"]}

    parts = judge.build_request("make a deck", pages)

    assert "make a deck" in parts[1][0]
    assert [text for text, image in parts if image is not None] == [
        "Deck P, page 1:",
        "Deck P, page 2:",
        "Deck Q, page 1:",
    ]
    assert [image for _, image in parts if image is not None][:2] == pages["Deck P"]


def test_a_failed_answer_is_asked_again_and_a_good_one_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(["not json", _answer()])
    monkeypatch.setattr(judge, "ask", lambda j, parts: (next(answers), {"input_tokens": 1}))
    monkeypatch.setattr(judge.time, "sleep", lambda s: None)

    answer, usage = judge.judge_round("deepseek:m", "b", {}, ["Deck P", "Deck Q"])

    assert answer["decks"]["Deck P"]["design"] == 4 and usage == {"input_tokens": 1}


def test_the_mean_and_spread_are_taken_over_the_rounds() -> None:
    records = [{"scores": {"design": 3.0, "content": 4}}, {"scores": {"design": 4.0, "content": 4}}]

    stats = judge.aggregate_scores(records)

    assert stats["design"] == {"mean": 3.5, "spread": 0.5, "n": 2.0}
    assert stats["content"]["spread"] == 0
    assert "coherence" not in stats


def _run(tmp_path: Path, name: str, cost: float, facts: int, design: list[float]) -> Path:
    folder = tmp_path / name / TASK
    (folder / "judge").mkdir(parents=True)
    result = {
        "task": TASK,
        "wall_seconds": 100,
        "tool_call_count": 10,
        "input_tokens": 5000,
        "cached_tokens": 4000,
        "output_tokens": 1000,
        "cost": cost,
    }
    checks = {
        "facts": {"found": facts, "total": 19},
        "pages": {"ok": True},
        "editability": {"ok": facts == 19},
        "inventions": {"count": 3},
        "layout": {"overflow_words": 0, "text_overlaps": 1},
    }
    (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
    (folder / "checks.json").write_text(json.dumps(checks), encoding="utf-8")
    for i, value in enumerate(design):
        record = {"scores": {"design": value, "content": 4.0, "coherence": 4.0}}
        (folder / "judge" / f"r{i}.json").write_text(json.dumps(record), encoding="utf-8")
    return tmp_path / name


def test_the_comparison_puts_both_runs_in_each_table(tmp_path: Path) -> None:
    a = _run(tmp_path, "baseline", 0.04, 19, [3.0, 4.0])
    b = _run(tmp_path, "engine", 0.06, 17, [4.5])

    table = compare.compare(a, b)

    assert "## baseline vs engine" in table
    assert "| 01-q3-review | 3.50 ±0.50 (n=2) | 4.50 ±0.00 (n=1) |" in table
    assert (
        "| 01-q3-review | 19/19 | 17/19 | yes | yes | yes | NO | 3 | 3 | 0 / 1 | 0 / 1 |" in table
    )
    assert "| **total** | 0.0400 | 0.0600 | 100 | 100 | 10 | 10 |" in table
    assert "| 02-security-training |" not in table


def test_a_task_only_one_run_has_shows_a_dash(tmp_path: Path) -> None:
    a = _run(tmp_path, "baseline", 0.04, 19, [3.0])
    (tmp_path / "empty").mkdir()

    table = compare.compare(a, tmp_path / "empty")

    assert "| 01-q3-review | 3.00 ±0.00 (n=1) | - |" in table
