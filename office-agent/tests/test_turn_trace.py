"""The record of how a turn went (`conversation/turn_record.py`, decision 0045)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from coscribe.conversation import turn_record
from coscribe.conversation.turn_record import TurnRecorder, turns_path


def _recorder(tmp_path: Path) -> TurnRecorder:
    return TurnRecorder(
        tmp_path, thread_id="t1", model="fake:model", effort="low", mode="manual", notice=False
    )


def _lines(tmp_path: Path) -> list[dict[str, Any]]:
    text = turns_path(tmp_path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def test_a_turn_is_one_line_with_its_calls_tokens_and_tools(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.usage(
        {"input_tokens": 100, "output_tokens": 20, "input_token_details": {"cache_read": 60}}
    )
    recorder.model_call()
    recorder.tool("read_file", is_error=False, result="the file's text")
    recorder.tool("read_file", is_error=True, result="No such file: plan.docx")
    recorder.usage({"input_tokens": 150, "output_tokens": 5})
    recorder.model_call()
    recorder.finish(stopped=False)

    [line] = _lines(tmp_path)
    assert (line["thread_id"], line["model"], line["effort"], line["mode"], line["notice"]) == (
        "t1",
        "fake:model",
        "low",
        "manual",
        False,
    )
    assert line["outcome"] == "completed" and line["error"] is None
    assert line["model_calls"] == 2
    assert (line["input_tokens"], line["cached_tokens"], line["output_tokens"]) == (250, 60, 25)
    assert line["tools"] == {"read_file": {"calls": 2, "errors": 1}}
    assert line["tool_errors"] == [{"tool": "read_file", "text": "No such file: plan.docx"}]
    assert line["seconds"] >= 0
    assert line["started"].endswith("+00:00")


def test_a_provider_that_reports_no_usage_adds_no_tokens(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.usage(None)
    recorder.model_call()
    recorder.finish(stopped=False)
    [line] = _lines(tmp_path)
    assert line["model_calls"] == 1
    assert line["input_tokens"] == 0


def test_a_successful_result_is_never_written(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.tool("read_file", is_error=False, result="salary of Ana: 5000")
    recorder.finish(stopped=False)
    assert "salary" not in turns_path(tmp_path).read_text(encoding="utf-8")


def test_an_error_text_is_cut_and_its_secrets_are_redacted(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    key = "sk-ant-" + "a" * 30
    recorder.tool("http_request", is_error=True, result=f"401 for {key} " + "x" * 1000)
    recorder.tool("use_connector", is_error=True, result={"error": "timeout"})
    recorder.finish(stopped=False)

    [line] = _lines(tmp_path)
    first, second = line["tool_errors"]
    assert key not in first["text"]
    assert "[REDACTED]" in first["text"]
    assert len(first["text"]) <= 300
    assert second["text"] == '{"error": "timeout"}'


def test_only_the_first_twenty_error_texts_are_kept_but_all_are_counted(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    for index in range(25):
        recorder.tool("run_script", is_error=True, result=f"failed {index}")
    recorder.finish(stopped=False)
    [line] = _lines(tmp_path)
    assert line["tools"]["run_script"] == {"calls": 25, "errors": 25}
    assert len(line["tool_errors"]) == 20


def test_a_turn_that_failed_keeps_the_exception_type_not_its_text(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.failed(RuntimeError("the user's sentence, quoted by a provider"))
    recorder.finish(stopped=False)
    [line] = _lines(tmp_path)
    assert line["outcome"] == "error"
    assert line["error"] == "RuntimeError"
    assert "sentence" not in turns_path(tmp_path).read_text(encoding="utf-8")


def test_a_retry_that_answered_is_not_an_error(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.failed(RuntimeError("first try"))
    recorder.model_call()
    recorder.finish(stopped=False)
    [line] = _lines(tmp_path)
    assert line["outcome"] == "completed"
    assert line["error"] is None


def test_a_stopped_turn_says_so(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path)
    recorder.model_call()
    recorder.finish(stopped=True)
    [line] = _lines(tmp_path)
    assert line["outcome"] == "stopped"


def test_a_turn_in_which_nothing_ran_writes_nothing(tmp_path: Path) -> None:
    _recorder(tmp_path).finish(stopped=False)
    assert not turns_path(tmp_path).exists()


def test_a_full_file_is_put_aside_and_a_new_one_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(turn_record, "_MAX_BYTES", 10)
    for stopped in (False, True):
        recorder = _recorder(tmp_path)
        recorder.model_call()
        recorder.finish(stopped=stopped)

    assert [line["outcome"] for line in _lines(tmp_path)] == ["stopped"]
    older = json.loads((tmp_path / "turns.1.jsonl").read_text(encoding="utf-8"))
    assert older["outcome"] == "completed"


def test_a_file_that_cannot_be_written_does_not_fail_the_turn(tmp_path: Path) -> None:
    blocked = tmp_path / "state"
    blocked.write_text("a file where the folder should be", encoding="utf-8")
    recorder = TurnRecorder(blocked, thread_id="t1")
    recorder.model_call()
    recorder.finish(stopped=False)
    assert blocked.read_text(encoding="utf-8") == "a file where the folder should be"


async def test_a_run_that_raises_is_counted_and_marked_failed(tmp_path: Path) -> None:
    async def run() -> Any:
        yield "updates", {"model": {"messages": [AIMessage(content="")]}}
        yield (
            "messages",
            (ToolMessage("boom", name="edit_docx", tool_call_id="c", status="error"), {}),
        )
        raise ConnectionError("provider went away")

    recorder = _recorder(tmp_path)
    seen = []
    with pytest.raises(ConnectionError):
        async for mode, _chunk in turn_record.observed(run(), recorder):
            seen.append(mode)
    recorder.finish(stopped=False)

    assert seen == ["updates", "messages"]
    [line] = _lines(tmp_path)
    assert (line["outcome"], line["error"], line["model_calls"]) == ("error", "ConnectionError", 1)
    assert line["tools"] == {"edit_docx": {"calls": 1, "errors": 1}}
