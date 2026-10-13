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


def _record(design: float, **more: object) -> dict[str, object]:
    return {
        "judge": judge.DEFAULT_JUDGE,
        "decks_in_request": 1,
        "scores": {"design": design, "content": 4.0, "coherence": 4.0},
        **more,
    }


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
        (folder / "judge" / f"r{i}.json").write_text(json.dumps(_record(value)), encoding="utf-8")
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
    assert "| **total (1 common tasks)** | 0.0400 | 0.0600 | 100 | 100 | 10 | 10 |" in table
    assert "| 02-security-training |" not in table


def test_a_task_only_one_run_has_shows_a_dash(tmp_path: Path) -> None:
    a = _run(tmp_path, "baseline", 0.04, 19, [3.0])
    (tmp_path / "empty").mkdir()

    table = compare.compare(a, tmp_path / "empty")

    assert "| 01-q3-review | 3.00 ±0.00 (n=1) | - |" in table


def test_scores_of_another_judge_or_a_joint_request_are_not_averaged_in(tmp_path: Path) -> None:
    a = _run(tmp_path, "a", 0.04, 19, [3.0])
    b = _run(tmp_path, "b", 0.04, 19, [3.0])
    folder = a / TASK / "judge"
    other = _record(1.0, judge="gemini:g")
    joint = _record(5.0, decks_in_request=2, runs=sorted(str(r.resolve()) for r in (a, b)))
    (folder / "gemini.json").write_text(json.dumps(other), encoding="utf-8")
    (folder / "joint.json").write_text(json.dumps(joint), encoding="utf-8")

    alone = judge.aggregate_scores(judge.load_records(a, TASK, judge.DEFAULT_JUDGE))
    together = judge.aggregate_scores(judge.load_records(a, TASK, judge.DEFAULT_JUDGE, [a, b]))
    gemini = judge.aggregate_scores(judge.load_records(a, TASK, "gemini:g"))

    assert alone["design"]["mean"] == 3.0 and alone["design"]["n"] == 1
    assert together["design"]["mean"] == 5.0
    assert gemini["design"]["mean"] == 1.0
    assert "| 01-q3-review | 3.00 ±0.00 (n=1) | 3.00 ±0.00 (n=1) |" in compare.compare(a, b)
    assert "5.00 ±0.00 (n=1) | -" in compare.compare(a, b, joint=True)


def _fake_decks(tmp_path: Path, names: list[str]) -> list[Path]:
    runs = []
    for name in names:
        render = tmp_path / name / TASK / "render"
        render.mkdir(parents=True)
        (render / "page-01.png").write_bytes(b"png")
        runs.append(tmp_path / name)
    return runs


def _answers(monkeypatch: pytest.MonkeyPatch, fail_first: bool = False) -> None:
    calls = {"n": 0}

    def fake(judge_name: str, brief: str, decks: dict, labels: list[str]) -> tuple[dict, dict]:
        calls["n"] += 1
        if fail_first and calls["n"] == 1:
            raise RuntimeError("rate limit")
        scores = {"design": 4, "content": 4, "coherence": 4, "defects": []}
        return {"decks": {label: scores for label in labels}, "ranking": labels}, {}

    monkeypatch.setattr(judge, "judge_round", fake)


def test_judging_a_second_pairing_keeps_the_records_of_the_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    a, b, c = _fake_decks(tmp_path, ["a", "b", "c"])
    _answers(monkeypatch)

    judge.judge_runs([a, b], [TASK], judge.DEFAULT_JUDGE, 1, 7)
    judge.judge_runs([a, c], [TASK], judge.DEFAULT_JUDGE, 1, 7)

    assert len(list((a / TASK / "judge").glob("*.json"))) == 2
    assert len(judge.load_records(a, TASK, joint_with=[a, b])) == 1
    assert len(judge.load_records(a, TASK, joint_with=[a, c])) == 1


def test_a_run_without_pages_does_not_stop_the_others_being_scored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    a, b = _fake_decks(tmp_path, ["a", "b"])
    empty = tmp_path / "empty"
    (empty / TASK).mkdir(parents=True)
    _answers(monkeypatch)

    judge.judge_runs([a, empty, b], [TASK], judge.DEFAULT_JUDGE, 1, 7)

    assert "empty has no rendered pages" in capsys.readouterr().out
    record = judge.load_records(a, TASK, joint_with=[a, b])[0]
    assert record["decks_in_request"] == 2


def test_one_failed_round_is_counted_and_the_batch_goes_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (a,) = _fake_decks(tmp_path, ["a"])
    _answers(monkeypatch, fail_first=True)

    failures = judge.judge_runs([a], [TASK], judge.DEFAULT_JUDGE, 2, 7)

    assert failures == 1 and len(judge.load_records(a, TASK)) == 1


def test_more_runs_than_labels_and_a_run_given_twice_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at most 8"):
        judge.check_runs([tmp_path / f"r{i}" for i in range(9)])
    with pytest.raises(ValueError, match="twice"):
        judge.check_runs([tmp_path / "a", tmp_path / "x" / ".." / "a"])


@pytest.mark.parametrize("bad", [True, False])
def test_a_boolean_is_not_a_score(bad: bool) -> None:
    with pytest.raises(ValueError, match="not a score"):
        judge.parse_answer(_answer(design=bad), ["Deck P", "Deck Q"])


@pytest.mark.parametrize(
    "ranking", [["P", "P"], ["P"], ["P", "Q", "Z"], ["P", "X"]], ids=lambda r: "-".join(r)
)
def test_a_ranking_that_is_not_each_deck_once_is_refused(ranking: list[str]) -> None:
    answer = json.loads(_answer())
    answer["ranking"] = ranking

    with pytest.raises(ValueError, match="ranking"):
        judge.parse_answer(json.dumps(answer), ["Deck P", "Deck Q"])


def test_defects_must_be_a_list_of_strings() -> None:
    answer = json.loads(_answer())
    answer["decks"]["P"]["defects"] = "overflow"

    with pytest.raises(ValueError, match="defects"):
        judge.parse_answer(json.dumps(answer), ["Deck P", "Deck Q"])


def test_a_client_error_is_not_retried_but_a_rate_limit_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import urllib.error

    def http(code: int) -> urllib.error.HTTPError:
        return urllib.error.HTTPError("u", code, "m", None, None)  # type: ignore[arg-type]

    assert not judge._retryable(http(403)) and not judge._retryable(http(400))
    assert judge._retryable(http(429)) and judge._retryable(http(503))
    assert judge._retryable(AttributeError("'list' object has no attribute 'items'"))
    calls = []

    def refuse(j: str, parts: list) -> tuple[str, dict]:
        calls.append(1)
        raise http(403)

    monkeypatch.setattr(judge, "ask", refuse)
    monkeypatch.setattr(judge.time, "sleep", lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        judge.judge_round("gemini:m", "b", {}, ["Deck P"])
    assert len(calls) == 1


def test_the_gemini_key_is_sent_in_a_header_not_the_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen = {}

    class Reply:
        def __enter__(self) -> Reply:
            return self

        def __exit__(self, *a: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}).encode()

    def fake_open(request: object, timeout: int) -> Reply:
        seen["url"] = request.full_url  # type: ignore[attr-defined]
        seen["headers"] = dict(request.header_items())  # type: ignore[attr-defined]
        return Reply()

    monkeypatch.setenv("GEMINI_API_KEY", "SECRET")
    monkeypatch.setattr(judge.urllib.request, "urlopen", fake_open)

    judge.ask_gemini("m", [("hi", None)])

    assert "SECRET" not in seen["url"] and seen["headers"]["X-goog-api-key"] == "SECRET"


def test_totals_only_cover_the_tasks_both_runs_have(tmp_path: Path) -> None:
    a = _run(tmp_path, "a", 0.04, 19, [3.0])
    b = _run(tmp_path, "b", 0.06, 19, [3.0])
    second = a / "02-security-training"
    second.mkdir()
    (second / "result.json").write_text(json.dumps({"cost": 9.0, "wall_seconds": 900}))

    table = compare.compare(a, b)

    assert "| 02-security-training |" in table
    assert "| **total (1 common tasks)** | 0.0400 | 0.0600 | 100 | 100 |" in table


def test_a_half_finished_task_and_an_old_result_file_do_not_crash_the_comparison(
    tmp_path: Path,
) -> None:
    a = _run(tmp_path, "a", 0.04, 19, [3.0])
    b = _run(tmp_path, "b", 0.06, 19, [3.0])
    (b / TASK / "checks.json").unlink()
    (a / TASK / "result.json").write_text(json.dumps({"cost": 0.04}))

    table = compare.compare(a, b)

    assert "| 01-q3-review | 0.0400 | 0.0600 | - | 100 | - | 10 | - |" in table


def test_runs_with_the_same_folder_name_get_different_columns(tmp_path: Path) -> None:
    first = _run(tmp_path / "x", "engine", 0.04, 19, [3.0])
    second = _run(tmp_path / "y", "engine", 0.06, 19, [3.0])

    table = compare.compare(first, second)

    assert "## x/engine vs y/engine" in table
