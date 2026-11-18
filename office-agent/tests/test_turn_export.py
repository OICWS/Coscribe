"""A failed turn written out as the start of an evaluation task (`conversation/turn_export.py`,
decision 0052)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from coscribe.conversation import eval_candidate, failed_turns, find_turn
from coscribe.conversation.turn_record import turns_path


def _line(started: str, thread_id: str = "t1", **fields: Any) -> dict[str, Any]:
    return {
        "started": started,
        "thread_id": thread_id,
        "kind": "conversation",
        "model": "fake:model",
        "outcome": "completed",
        "error": None,
        "model_calls": 2,
        "tools": {"read_file": {"calls": 1, "errors": 0}},
        "tool_errors": [],
        **fields,
    }


def _write(path: Path, *lines: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def test_only_this_conversations_failed_turns_are_listed_newest_first(tmp_path: Path) -> None:
    current = turns_path(tmp_path)
    _write(
        current.with_suffix(".1.jsonl"),
        _line("2026-11-01T10:00:00+00:00", outcome="error", error="TimeoutError"),
    )
    _write(
        current,
        _line("2026-11-02T10:00:00+00:00"),
        _line("2026-11-03T10:00:00+00:00", outcome="stopped"),
        _line("2026-11-04T10:00:00+00:00", thread_id="other", outcome="error"),
        _line(
            "2026-11-05T10:00:00+00:00",
            tools={"edit_docx": {"calls": 2, "errors": 1}},
            tool_errors=[{"tool": "edit_docx", "text": "No paragraph 9"}],
        ),
    )
    with current.open("a", encoding="utf-8") as handle:
        handle.write("not json\n")

    turns = failed_turns(tmp_path, "t1")

    assert [turn["turn"]["started"][:10] for turn in turns] == [
        "2026-11-05",
        "2026-11-03",
        "2026-11-01",
    ]
    assert turns[0]["tool_errors"] == [{"tool": "edit_docx", "text": "No paragraph 9"}]
    assert turns[2]["turn"]["error"] == "TimeoutError"


def test_no_record_lists_nothing(tmp_path: Path) -> None:
    assert failed_turns(tmp_path, "t1") == []
    assert find_turn(tmp_path, "t1", "2026-11-01T10:00:00+00:00") is None


def test_the_file_keeps_named_fields_only_and_drops_the_conversation_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: Path("/home/collins"))
    line = _line(
        "2026-11-05T10:00:00+00:00",
        outcome="error",
        some_later_field="what the person typed",
        tool_errors=[{"tool": "read_file", "text": "No such file: /home/collins/q3/budget.xlsx"}],
    )

    candidate = eval_candidate(
        line,
        asked="  Sum the budget in /home/collins/q3 with key sk-ant-abcdefghijklmnopqrstuvwxyz  ",
        went_wrong="It read the wrong file.",
    )

    assert candidate["format"] == "coscribe-failed-turn/1"
    assert "thread_id" not in candidate["turn"]
    assert "some_later_field" not in candidate["turn"]
    assert candidate["turn"]["outcome"] == "error"
    assert candidate["tool_errors"] == [
        {"tool": "read_file", "text": "No such file: ~/q3/budget.xlsx"}
    ]
    assert candidate["asked"] == "Sum the budget in ~/q3 with key [REDACTED]"
    assert candidate["went_wrong"] == "It read the wrong file."
    assert "collins" not in json.dumps(candidate)


def test_a_turn_is_found_by_its_start_time_in_its_own_conversation(tmp_path: Path) -> None:
    _write(turns_path(tmp_path), _line("2026-11-05T10:00:00+00:00", outcome="error"))
    assert find_turn(tmp_path, "t1", "2026-11-05T10:00:00+00:00") is not None
    assert find_turn(tmp_path, "other", "2026-11-05T10:00:00+00:00") is None
