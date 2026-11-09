"""The record of how a turn went (`runtime_lg/trace.py`, decision 0045)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from coscribe.runtime_lg import trace
from coscribe.runtime_lg import TraceLog, TurnRecorder, TurnTrace, tool_failure_rates


def _recorder(tmp_path: Path) -> TurnRecorder:
    return TurnRecorder(
        TraceLog(tmp_path), thread_id="t1", model="fake:model", effort="low", mode="manual"
    )


def test_a_turn_is_one_line_with_its_calls_tokens_and_tools(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.model_call(
        {"input_tokens": 100, "output_tokens": 20, "input_token_details": {"cache_read": 60}}
    )
    recorder.tool("read_file", is_error=False, result="the file's text")
    recorder.tool("read_file", is_error=True, result="No such file: plan.docx")
    recorder.model_call({"input_tokens": 150, "output_tokens": 5})
    recorder.finish("completed")

    [entry] = TraceLog(tmp_path).read_all()
    assert (entry.thread_id, entry.model, entry.effort, entry.mode) == (
        "t1",
        "fake:model",
        "low",
        "manual",
    )
    assert entry.outcome == "completed" and entry.error is None
    assert (entry.model_calls, entry.input_tokens, entry.cached_tokens, entry.output_tokens) == (
        2,
        250,
        60,
        25,
    )
    assert entry.tools == {"read_file": {"calls": 2, "errors": 1}}
    assert entry.tool_errors == [{"tool": "read_file", "text": "No such file: plan.docx"}]
    assert entry.seconds >= 0


def test_a_model_call_without_usage_still_counts(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.model_call(None)
    recorder.finish("completed")
    [entry] = TraceLog(tmp_path).read_all()
    assert entry.model_calls == 1
    assert entry.input_tokens == 0


def test_a_successful_result_is_never_written(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.model_call(None)
    recorder.tool("read_file", is_error=False, result="salary of Ana: 5000")
    recorder.finish("completed")
    assert "salary" not in TraceLog(tmp_path).path.read_text(encoding="utf-8")


def test_an_error_text_is_cut_and_its_secrets_are_redacted(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    key = "sk-ant-" + "a" * 30
    recorder.tool("http_request", is_error=True, result=f"401 for {key} " + "x" * 1000)
    recorder.tool("use_connector", is_error=True, result={"error": "timeout"})
    recorder.finish("completed")

    [entry] = TraceLog(tmp_path).read_all()
    first, second = entry.tool_errors
    assert key not in first["text"]
    assert "[REDACTED]" in first["text"]
    assert len(first["text"]) <= 300
    assert second["text"] == '{"error": "timeout"}'


def test_only_the_first_twenty_error_texts_are_kept_but_all_are_counted(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    for index in range(25):
        recorder.tool("run_script", is_error=True, result=f"failed {index}")
    recorder.finish("completed")
    [entry] = TraceLog(tmp_path).read_all()
    assert entry.tools["run_script"] == {"calls": 25, "errors": 25}
    assert len(entry.tool_errors) == 20


def test_a_turn_that_failed_keeps_the_exception_type_not_its_text(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.finish("error", RuntimeError("the user's sentence, quoted by a provider"))
    [entry] = TraceLog(tmp_path).read_all()
    assert entry.outcome == "error"
    assert entry.error == "RuntimeError"
    assert "sentence" not in TraceLog(tmp_path).path.read_text(encoding="utf-8")


def test_a_turn_in_which_nothing_ran_writes_nothing(tmp_path: Path) -> None:
    _recorder(tmp_path).finish("completed")
    assert not TraceLog(tmp_path).path.exists()


def test_finish_writes_once(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.model_call(None)
    recorder.finish("stopped")
    recorder.finish("completed")
    [entry] = TraceLog(tmp_path).read_all()
    assert entry.outcome == "stopped"


def test_a_line_that_does_not_parse_is_skipped(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.model_call(None)
    recorder.finish("completed")
    log = TraceLog(tmp_path)
    with log.path.open("a", encoding="utf-8") as handle:
        handle.write('{"cut off\n')
        handle.write(json.dumps({"unknown": 1}) + "\n")
    assert len(log.read_all()) == 1


def test_a_full_file_is_put_aside_and_a_new_one_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trace, "_MAX_BYTES", 10)
    outcomes: tuple[Any, ...] = ("completed", "stopped")
    for outcome in outcomes:
        recorder = _recorder(tmp_path)
        recorder.model_call(None)
        recorder.finish(outcome)

    log = TraceLog(tmp_path)
    assert [entry.outcome for entry in log.read_all()] == ["stopped"]
    older = json.loads((tmp_path / "turns.1.jsonl").read_text(encoding="utf-8"))
    assert older["outcome"] == "completed"


def test_a_log_that_cannot_be_written_does_not_fail_the_turn(tmp_path: Path) -> None:
    blocked = tmp_path / "state"
    blocked.write_text("a file where the folder should be", encoding="utf-8")
    recorder = TurnRecorder(
        TraceLog(blocked), thread_id="t1", model="m", effort="low", mode="manual"
    )
    recorder.model_call(None)
    recorder.finish("completed")
    assert blocked.is_file()


def test_tool_failure_rates_put_the_tool_that_fails_most_first() -> None:
    def turn(tools: dict[str, dict[str, int]]) -> TurnTrace:
        return TurnTrace(
            started="2026-11-10T00:00:00+00:00",
            thread_id="t",
            model="m",
            effort="low",
            mode="manual",
            notice=False,
            seconds=1.0,
            outcome="completed",
            error=None,
            model_calls=1,
            input_tokens=0,
            cached_tokens=0,
            output_tokens=0,
            tools=tools,
        )

    rows = tool_failure_rates(
        [
            turn({"read_file": {"calls": 5, "errors": 0}, "edit_docx": {"calls": 2, "errors": 1}}),
            turn({"edit_docx": {"calls": 3, "errors": 2}, "run_script": {"calls": 1, "errors": 1}}),
        ]
    )
    assert rows == [("edit_docx", 5, 3), ("run_script", 1, 1), ("read_file", 5, 0)]
