"""What a turn the user stopped leaves in the history for the next one."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from coscribe.conversation.stopped_turn import keep_stopped_turn
from coscribe.runtime_lg import stopped_turn_messages
from coscribe.runtime_lg.messages import is_plan_check, starts_a_turn
from coscribe.runtime_lg.tool_calls import ORPHANED_TOOL_CALL_NOTE


def _turn() -> list[Any]:
    wrapped = {"name": "run_python_script", "arguments": {"script": "..."}}
    return [
        HumanMessage(content="earlier request"),
        AIMessage(content="", tool_calls=[{"id": "c0", "name": "read_file", "args": {}}]),
        ToolMessage(content=ORPHANED_TOOL_CALL_NOTE, tool_call_id="c0", name="read_file"),
        HumanMessage(content="count the rows"),
        AIMessage(content="", tool_calls=[{"id": "c1", "name": "use_tool", "args": wrapped}]),
        ToolMessage(content=ORPHANED_TOOL_CALL_NOTE, tool_call_id="c1", name="use_tool"),
    ]


def test_the_reply_so_far_is_kept_and_the_note_names_this_turns_cut_calls() -> None:
    added = stopped_turn_messages(_turn(), "Counting now.", ['"sync the folder"'])

    reply, note = added
    assert reply.content == "Counting now.\n\n[stopped]"
    assert is_plan_check(note) and not starts_a_turn(note)
    assert "cut off and did not finish: run_python_script." in note.content
    assert "read_file" not in note.content  # an earlier turn's
    assert 'not stopped: "sync the folder"' in note.content


def test_a_reply_already_in_the_history_is_not_added_twice_and_silence_adds_only_the_note() -> None:
    messages = [HumanMessage(content="hi"), AIMessage(content="Done.")]

    assert len(stopped_turn_messages(messages, "Done.", [])) == 1
    assert len(stopped_turn_messages(messages, "", [])) == 1


async def test_a_conversation_being_deleted_is_not_written_back(tmp_path: Path) -> None:
    class Untouchable:
        async def aget_state(self, config: Any) -> Any:
            raise AssertionError("a deleted conversation was read back")

    host = SimpleNamespace(
        thread_id="t1",
        settings=SimpleNamespace(state_dir=tmp_path),
        lg_agent=Untouchable(),
        config={},
        _stop_requested=True,
    )

    shown = await keep_stopped_turn(cast(Any, host), "half", keep=False)
    assert shown == "half\n\n[stopped]"


async def test_a_dropped_socket_keeps_nothing() -> None:
    host = SimpleNamespace(lg_agent=None, _stop_requested=False)

    assert await keep_stopped_turn(cast(Any, host), "half") == "[stopped]"


def test_a_question_left_open_by_the_stop_is_not_asked_again_first_thing() -> None:
    messages = [
        HumanMessage(content="tidy the folder"),
        AIMessage(content="", tool_calls=[{"id": "q1", "name": "ask_user_question", "args": {}}]),
        ToolMessage(content="(Stopped by user before answering.)", tool_call_id="q1"),
    ]

    note = stopped_turn_messages(messages, "", [])[-1]

    assert "question was left unanswered" in note.content
    assert "cut off" not in note.content
