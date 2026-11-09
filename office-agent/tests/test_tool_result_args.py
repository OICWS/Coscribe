"""A tool result shows its own call's arguments when calls made together finish out of order."""

from coscribe.conversation.turn_stream import _take_args


def test_a_result_takes_the_arguments_of_the_call_it_answers() -> None:
    pending = [("c1", {"path": "a.txt"}), ("c2", {"path": "b.txt"})]

    assert _take_args(pending, "c2") == {"path": "b.txt"}
    assert _take_args(pending, "c1") == {"path": "a.txt"}
    assert pending == []


def test_a_result_without_a_known_id_takes_the_oldest_call_of_its_name() -> None:
    pending = [("c1", {"path": "a.txt"}), ("c2", {"path": "b.txt"})]

    assert _take_args(pending, "other") == {"path": "a.txt"}
    assert _take_args([], "c1") == {}
