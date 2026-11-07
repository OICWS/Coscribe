# ruff: noqa: E402
"""Web tests: a stopped turn keeps what it said and did, and the next turn knows it was stopped."""

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from .helpers import _client_lg, _receive_until


class TalksThenHangs(BaseChatModel):
    """The first call streams part of a reply and then waits forever, as a provider call that
    stalls mid-answer; later calls answer at once and keep what they were sent."""

    started: Any = None
    seen: list[list[BaseMessage]] = []
    calls: int = 0

    def bind_tools(self, tools: Any, *, tool_choice: str | None = None, **kwargs: Any) -> Any:
        return self

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        self.seen.append(list(messages))
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="Sure, a shorter one."))]
        )

    async def _astream(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> Any:
        self.calls += 1
        if self.calls > 1:
            self.seen.append(list(messages))
            yield ChatGenerationChunk(message=AIMessageChunk(content="Sure, a shorter one."))
            return
        yield ChatGenerationChunk(
            message=AIMessageChunk(content="Here is the long report, part one.")
        )
        self.started.set()
        await asyncio.sleep(999)

    @property
    def _llm_type(self) -> str:
        return "talks-then-hangs"


def test_a_stopped_reply_stays_in_the_history_and_the_next_turn_hears_of_the_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = threading.Event()
    model = TalksThenHangs(started=started, seen=[])
    with _client_lg(tmp_path, monkeypatch, model) as client:
        with client.websocket_connect("/ws/t_keep") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "write the long report"})
            assert started.wait(timeout=5)
            ws.send_json({"type": "stop"})
            stopped = _receive_until(ws, "agent_message")[-1]
        with client.websocket_connect("/ws/t_keep") as ws:
            ws.receive_json()  # state
            history = ws.receive_json()
            ws.send_json({"type": "user_message", "text": "make it shorter"})
            _receive_until(ws, "agent_message")

    kept = "Here is the long report, part one."
    assert stopped["text"] == f"{kept}\n\n[stopped]"
    assert history["entries"][-1] == {"kind": "agent", "text": f"{kept}\n\n[stopped]"}
    [sent] = model.seen
    note = next(str(m.content) for m in sent if "pressed Stop" in str(m.content))
    assert "don't take the stopped work up again" in note
    assert kept in "".join(str(m.content) for m in sent)
    assert str(sent[-1].content).endswith("make it shorter")
