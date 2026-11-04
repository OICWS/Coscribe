from pathlib import Path

from coscribe.config import Settings
from coscribe.coordinator import build_coordinator_agent
from coscribe.tools._output_truncation import MAX_SCRIPT_OUTPUT_CHARS, truncate_script_output
from coscribe.tools.exec.running import Detachable


def test_truncate_script_output_is_a_no_op_under_the_cap() -> None:
    text = "hello\n" * 100
    assert len(text) <= MAX_SCRIPT_OUTPUT_CHARS
    assert truncate_script_output(text) == text


def test_truncate_script_output_is_a_no_op_exactly_at_the_cap() -> None:
    text = "x" * MAX_SCRIPT_OUTPUT_CHARS
    assert truncate_script_output(text) == text


def test_truncate_script_output_keeps_both_ends_past_the_cap() -> None:
    head = "HEAD_MARKER" + "a" * 50_000
    tail = "b" * 50_000 + "TAIL_MARKER"
    text = head + tail

    result = truncate_script_output(text)

    assert len(result) < len(text)
    assert result.startswith("HEAD_MARKER")
    assert result.endswith("TAIL_MARKER")
    assert "characters truncated" in result


def test_truncate_script_output_reports_the_real_omitted_count() -> None:
    text = "x" * (MAX_SCRIPT_OUTPUT_CHARS + 1_234)

    result = truncate_script_output(text)

    # 4000 head + 4000 tail kept -- everything else in between is the
    # reported omitted count.
    expected_omitted = len(text) - 4_000 - 4_000
    assert f"{expected_omitted:,} characters truncated" in result


def test_truncate_script_output_keeps_the_whole_text_in_a_file_it_names(tmp_path: Path) -> None:
    text = "HEAD" + "x" * 50_000 + "MIDDLE" + "y" * 50_000 + "TAIL"

    result = truncate_script_output(text, tmp_path / "out", "stderr")

    saved = next((tmp_path / "out").glob("*-stderr.txt"))
    assert saved.read_text(encoding="utf-8") == text
    assert str(saved) in result
    assert "MIDDLE" not in result


def test_truncate_script_output_saves_nothing_under_the_cap(tmp_path: Path) -> None:
    assert truncate_script_output("short", tmp_path / "out") == "short"
    assert not (tmp_path / "out").exists()


def test_the_conversations_file_tools_read_its_kept_script_output(tmp_path: Path) -> None:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        default_model="anthropic:claude-sonnet-4-5",
        workspace_root=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        skills_dir=tmp_path / "skills",
        memory_path=tmp_path / "MEMORY.md",
    )
    keep = Detachable("thread-1", lambda *args: "").cut_output_dir(settings.state_dir)
    saved = truncate_script_output("z" * (MAX_SCRIPT_OUTPUT_CHARS + 1), keep)
    path = next(keep.glob("*.txt"))
    assert str(path) in saved

    agent = build_coordinator_agent(settings, "thread-1")
    read_file = next(t for t in agent.tools if t.__name__ == "read_file")  # type: ignore[attr-defined]

    assert read_file(str(path), head=1).startswith("zzz")
