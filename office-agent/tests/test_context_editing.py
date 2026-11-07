from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately

from coscribe.runtime_lg.context_editing import KEEP, PLACEHOLDER, STEP, ClearOldToolResults


def clear_old_tool_results(messages: list[Any], trigger_tokens: int) -> list[Any]:
    edited = list(messages)
    ClearOldToolResults(trigger_tokens).apply(edited, count_tokens=count_tokens_approximately)
    return edited


def _thread(results: int, name: str = "read_file") -> list[BaseMessage]:
    messages: list[BaseMessage] = [HumanMessage(content="Summarize the reports.")]
    for i in range(results):
        messages.append(
            AIMessage(content="", tool_calls=[{"name": name, "args": {}, "id": f"c{i}"}])
        )
        messages.append(ToolMessage(content="x " * 500, name=name, tool_call_id=f"c{i}"))
    return messages


def _cleared(messages: list[BaseMessage]) -> int:
    return sum(isinstance(m, ToolMessage) and m.content == PLACEHOLDER for m in messages)


def test_nothing_is_cleared_under_the_trigger() -> None:
    messages = _thread(30)

    assert clear_old_tool_results(messages, trigger_tokens=10_000_000) == messages


def test_older_results_are_cleared_in_steps_and_the_newest_are_kept() -> None:
    edited = clear_old_tool_results(_thread(KEEP + STEP + 3), trigger_tokens=100)

    assert _cleared(edited) == STEP
    newest = [m for m in edited if isinstance(m, ToolMessage)][-KEEP:]
    assert all(m.content != PLACEHOLDER for m in newest)


def test_the_cleared_boundary_holds_until_a_full_step_more_results_arrive() -> None:
    """A moved boundary changes an earlier message, which loses the provider's cached prefix
    from there on; it should move once every STEP results, not on every call."""
    counts = {
        n: _cleared(clear_old_tool_results(_thread(n), trigger_tokens=100))
        for n in range(KEEP + STEP, KEEP + 2 * STEP)
    }

    assert set(counts.values()) == {STEP}
    assert _cleared(clear_old_tool_results(_thread(KEEP + 2 * STEP), 100)) == 2 * STEP


def test_the_plan_and_skills_are_never_cleared() -> None:
    edited = clear_old_tool_results(_thread(KEEP + 2 * STEP, name="load_skill"), 100)

    assert _cleared(edited) == 0


def test_the_history_itself_is_not_changed() -> None:
    messages = _thread(KEEP + STEP)

    clear_old_tool_results(messages, trigger_tokens=100)

    assert _cleared(messages) == 0
