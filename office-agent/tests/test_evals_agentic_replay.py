"""The multi-turn tasks run again from their tapes (`evals/agentic/replay.py`): the agent loop,
its middleware and every tool run for real on the answers a model once gave. No model is called."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from evals.agentic import replay, run, tasks

TAPE_FILES = sorted(replay.TAPES.glob("*.json"))


@pytest.fixture(autouse=True)
def _as_the_evaluation_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tapes were recorded in the shipped permission mode (Auto, whose reviewer's verdicts
    are answers on the tape); the test suite's default is Manual. A replay needs no key."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("COSCRIBE_DEFAULT_PERMISSION_MODE")


def _answer(text: str = "", tools: int = 0) -> AIMessage:
    calls = [
        {"name": "read_file", "args": {"path": f"{n}.txt"}, "id": f"c{n}"} for n in range(tools)
    ]
    return AIMessage(content=text, tool_calls=calls)


def test_there_are_tapes_to_run() -> None:
    assert len(TAPE_FILES) >= 2


@pytest.mark.parametrize("tape_file", TAPE_FILES, ids=lambda path: path.stem)
async def test_a_recorded_task_runs_the_same_from_its_tape(tape_file: Path, tmp_path: Path) -> None:
    [task] = tasks.select(tape_file.stem)

    result = await run.replay_task(task, tape_file, tmp_path)

    assert result["errors"] == []
    assert result["tape"] == {"answers_left": 0, "calls_as_recorded": True}
    assert result["completed"], result["checks"]
    assert result["model_calls"] == 0


async def test_a_tape_one_answer_short_fails_and_says_to_record_again(
    tmp_path: Path,
) -> None:
    source = replay.TAPES / "10-twelve-files.json"
    recorded = json.loads(source.read_text(encoding="utf-8"))
    last_agent = max(i for i, entry in enumerate(recorded["entries"]) if entry["kind"] == "agent")
    del recorded["entries"][last_agent]
    short = tmp_path / "10-twelve-files.json"
    short.write_text(json.dumps(recorded), encoding="utf-8")
    [task] = tasks.select("10")

    result = await run.replay_task(task, short, tmp_path / "out")

    assert any("record the tape again" in error for error in result["errors"])


def test_answers_of_a_kind_come_back_in_order_and_the_kinds_do_not_mix() -> None:
    tape = replay.Tape("t")
    tape.add("agent", _answer("first", tools=1))
    tape.add("side", _answer("a title"))
    tape.add("agent", _answer("second"))

    assert tape.next("agent").content == "first"
    assert tape.next("agent").content == "second"
    assert tape.left() == 1
    assert tape.next("side").content == "a title"
    with pytest.raises(replay.TapeMismatch, match="one more side answer"):
        tape.next("side")


def test_a_saved_tape_names_no_folder_of_the_run_that_made_it(tmp_path: Path) -> None:
    root = tmp_path / "run one"
    workspace = root / "workspace"
    tape = replay.Tape("t", "deepseek:deepseek-flash", "low", window=1000)
    tape.add(
        "agent",
        AIMessage(
            content=f"Saved to {workspace / 'out.txt'}",
            tool_calls=[{"name": "write_file", "args": {"path": str(root / "x")}, "id": "c1"}],
            usage_metadata={"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
            response_metadata={"model_provider": "openai"},
        ),
    )
    tape.calls = [["write_file"]]
    file = tmp_path / "tape.json"

    tape.save(file, workspace, root)

    assert str(tmp_path) not in file.read_text(encoding="utf-8")
    other = tmp_path / "run two"
    loaded = replay.Tape.load(file, other / "workspace", other)
    answer = loaded.next("agent")
    assert answer.content == f"Saved to {other / 'workspace' / 'out.txt'}"
    assert answer.tool_calls[0]["args"] == {"path": str(other / "x")}
    assert answer.usage_metadata == {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7}
    assert (loaded.window, loaded.provider, loaded.effort) == (1000, "openai", "low")
    assert loaded.calls == [["write_file"]]


def test_the_agent_is_told_from_a_side_job_by_how_many_tools_it_is_given() -> None:
    model = replay.TapeModel()
    tape = replay.Tape("t")
    tape.add("side", _answer("verdict"))
    tape.add("agent", _answer("reply"))
    replay.use(tape)

    assert model.bind_tools([object()] * 40).invoke("hi").content == "reply"
    assert model.bind_tools([object()]).invoke("hi").content == "verdict"
