from collections.abc import Iterator

import pytest

from coscribe.conversation import wire

from .wire_check import WireError, check_client_message, check_event, violations


@pytest.fixture(autouse=True)
def _forget_deliberate_violations() -> Iterator[None]:
    yield
    violations.clear()


def test_a_valid_event_passes() -> None:
    assert check_event({"type": "agent_delta", "text": "hi"}) is None
    assert check_event({"type": "usage", "total_tokens": 3, "cache_read_tokens": 1}) is None
    history = {"type": "history", "entries": [{"kind": "user", "text": "x"}], "has_older": False}
    assert check_event(history) is None


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"type": "agent_delta"}, "missing keys \\['text'\\]"),
        ({"type": "agent_delta", "text": "x", "extra": 1}, "unexpected keys \\['extra'\\]"),
        ({"type": "no_such_event"}, "unknown event type"),
        ({"type": "agent_delta", "text": 3}, "expected str"),
        ({"type": "compacted", "before": True, "after": 1, "elapsed_ms": 2}, "expected an int"),
        ({"type": "history", "entries": [{"kind": "x"}], "has_older": False}, "no member"),
    ],
)
def test_a_payload_that_breaks_the_contract_fails(payload: dict[str, object], message: str) -> None:
    with pytest.raises(WireError, match=message):
        check_event(payload)


def test_question_responses_are_told_apart_by_their_keys() -> None:
    for body in ({"answer": "x"}, {"answers": ["x", None]}, {"dismissed": True}):
        assert check_client_message({"type": "question_response", "id": "a", **body}) is None
    with pytest.raises(WireError):
        check_client_message({"type": "question_response", "id": "a", "dismissed": False})


def test_the_step_record_typeddict_has_the_dataclass_fields() -> None:
    from dataclasses import fields

    from coscribe.workflows.engine import StepRecord

    assert set(wire.WorkflowStepRecord.__annotations__) == {f.name for f in fields(StepRecord)}


def test_an_annotation_the_checker_cannot_read_is_refused_clearly() -> None:
    from .wire_check import _check

    with pytest.raises(WireError, match="does not support"):
        _check((1,), tuple[int, ...], "x")
