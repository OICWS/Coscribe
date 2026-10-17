# ruff: noqa: E402
"""Web tests: compaction, paging back, editing and rewinding a message."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import (
    AIMessage,
)

from .helpers import (
    FakeToolCallingChatModel,
    GrpcMetadataOverflowThenSuccessModel,
    _client_lg,
    _receive_until,
)


def test_compact_refuses_when_nothing_to_compact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t4f") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "/compact"})
            error = ws.receive_json()

    assert error["type"] == "error"
    assert "Nothing much to compact" in error["message"]


def test_load_older_messages_across_two_compactions_reveals_each_epoch_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(content="reply one-a"),
            AIMessage(content="reply one-b"),
            AIMessage(content="first summary"),
            AIMessage(content="reply two-a"),
            AIMessage(content="reply two-b"),
            AIMessage(content="second summary"),
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_older3") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            # /compact refuses below 4 messages (see _handle_compact) --
            # two turns per epoch here, same as
            # test_compact_collapses_history_and_survives_a_later_turn.
            ws.send_json({"type": "user_message", "text": "turn one-a"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "turn one-b"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "/compact"})
            assert ws.receive_json()["type"] == "compacted"

            ws.send_json({"type": "user_message", "text": "turn two-a"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "turn two-b"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "/compact"})
            assert ws.receive_json()["type"] == "compacted"

            ws.send_json({"type": "load_older_messages"})
            first_older = ws.receive_json()
            ws.send_json({"type": "load_older_messages"})
            second_older = ws.receive_json()
            ws.send_json({"type": "load_older_messages"})
            third_older = ws.receive_json()

    # The first compact's own synthetic note is a real HumanMessage
    # aupdate_state adds -- it becomes message #1 of the *next* epoch
    # going forward (the model's context after a compact genuinely
    # starts from that note), so it's what this epoch's own full
    # accumulated list starts with, same as the live conversation would
    # have shown it during epoch two itself.
    first_texts = [(e["kind"], e.get("text")) for e in first_older["entries"]]
    assert first_texts[0][0] == "user"
    assert "first summary" in first_texts[0][1]
    assert first_texts[1:] == [
        ("user", "turn two-a"),
        ("agent", "reply two-a"),
        ("user", "turn two-b"),
        ("agent", "reply two-b"),
    ]
    assert first_older["has_more"] is True
    assert [(e["kind"], e.get("text")) for e in second_older["entries"]] == [
        ("user", "turn one-a"),
        ("agent", "reply one-a"),
        ("user", "turn one-b"),
        ("agent", "reply one-b"),
    ]
    assert second_older["has_more"] is True
    # Nothing left before the very first turn -- and critically, this does
    # NOT re-return the first epoch's messages a second time (the real bug
    # a naive "always subset-check against the current checkpoint" version
    # of this would have hit -- see load_older_messages' own docstring).
    assert third_older == {"type": "older_messages", "entries": [], "has_more": False}


def test_edit_message_rejects_anything_but_the_latest_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="hi there!"), AIMessage(content="nice to hear")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_edit_old") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "how are you"})
            _receive_until(ws, "tasks_changed")

            ws.send_json({"type": "edit_message", "index": 0, "text": "hello, edited"})
            error = ws.receive_json()

        with client.websocket_connect("/ws/t_edit_old") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert error["type"] == "error"
    assert "most recent message" in error["message"]
    assert [e["text"] for e in history["entries"]] == [
        "hello",
        "hi there!",
        "how are you",
        "nice to hear",
    ]


def test_edit_message_rejects_an_out_of_range_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_edit2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")

            ws.send_json({"type": "edit_message", "index": 5, "text": "no such turn"})
            error = ws.receive_json()

    assert error["type"] == "error"
    assert "No such message to edit" in error["message"]


def test_rewind_message_truncates_without_regenerating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a real, live-reported bug: the UI's "Rewind"
    button used to call edit_message with the turn's own unedited text,
    which truncates *and* immediately reruns it -- that's retry, not
    rewind. rewind_message must truncate and stop there, with no new turn
    (and so no new agent_message) following it."""
    fake_model = FakeToolCallingChatModel(
        responses=[AIMessage(content="hi there!"), AIMessage(content="nice to hear")]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_rewind1") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")
            ws.send_json({"type": "user_message", "text": "how are you"})
            _receive_until(ws, "tasks_changed")

            # index 1 -- the second turn -- rewound. Only that turn's own
            # "how are you"/"nice to hear" is discarded; the first turn is
            # untouched, and nothing regenerates in its place.
            ws.send_json({"type": "rewind_message", "index": 1})
            rewound = ws.receive_json()

        with client.websocket_connect("/ws/t_rewind1") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()

    assert rewound == {"type": "rewound", "index": 1}
    assert history["entries"] == [
        {"kind": "user", "text": "hello"},
        {"kind": "agent", "text": "hi there!"},
    ]


def test_rewind_message_rejects_an_out_of_range_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi there!")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_rewind2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            _receive_until(ws, "tasks_changed")

            ws.send_json({"type": "rewind_message", "index": 5})
            error = ws.receive_json()

    assert error["type"] == "error"
    assert "No such message to rewind" in error["message"]


def test_grpc_metadata_overflow_recovers_by_rebuilding_the_agent_and_retrying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a real, live-reported bug: a long-lived Gemini
    session's gRPC channel accumulates something into its own metadata
    until a call fails with "429 ... Stream removed (received metadata
    size exceeds soft limit ...)" -- session.py's own
    _GRPC_METADATA_OVERFLOW_SIGNATURE comment has the full explanation.
    The turn must recover by rebuilding self.model/self.lg_agent and
    retrying once, not surface that error to the user on the first hit."""
    fake_model = GrpcMetadataOverflowThenSuccessModel(responses=[AIMessage(content="recovered")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_grpc_overflow") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            messages = _receive_until(ws, "tasks_changed")

    agent_message = next(m for m in messages if m["type"] == "agent_message")
    assert agent_message["text"] == "recovered"
    assert not any(m["type"] == "error" for m in messages)
    assert fake_model.calls == 2
