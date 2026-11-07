"""The sentence the simple view opens a task with: written once per saved version, kept when the
person wrote it, and none (not an error) when no model answers."""

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from coscribe.web.routes import scheduled

from .helpers import FakeToolCallingChatModel, _client_lg


class _Counting:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.seen: list[Any] = []

    async def ainvoke(self, messages: Any, config: Any = None) -> AIMessage:
        self.seen.append(messages)
        if not self.replies:
            raise RuntimeError("no model")
        return AIMessage(content=self.replies.pop(0))


def _task(title: str) -> dict[str, Any]:
    step = {
        "id": "s",
        "kind": "tool",
        "title": title,
        "tool": "read_file",
        "args": {"path": "a.md"},
    }
    return {"name": "Notes", "kind": "manual", "at": "", "workflow": {"steps": [step]}}


def test_overview_is_written_once_per_version_and_kept_when_yours_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = _Counting('"Reads your notes and tells you what changed."', "Reads the new notes.")
    monkeypatch.setattr(scheduled, "_overview_model", lambda _settings: model)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        trigger_id = client.post("/api/scheduled-tasks", json=_task("Read the notes")).json()[
            "trigger_id"
        ]
        path = f"/api/scheduled-tasks/{trigger_id}/overview"
        first = client.get(path).json()
        again = client.get(path).json()
        client.put(f"/api/scheduled-tasks/{trigger_id}", json=_task("Read the new notes"))
        changed = client.get(path).json()
        mine = client.put(path, json={"text": "  My   own words. "}).json()
        client.put(f"/api/scheduled-tasks/{trigger_id}", json=_task("Read old notes"))
        kept = client.get(path).json()
        cleared = client.put(path, json={"text": ""}).json()
        none_left = client.get(path).json()

    assert first == {
        "text": "Reads your notes and tells you what changed.",
        "version": 1,
        "by": "ai",
    }
    assert again == first
    assert changed == {"text": "Reads the new notes.", "version": 2, "by": "ai"}
    assert len(model.seen) == 3  # the third is the call after clearing, which had nothing to say
    assert "Read the notes" in model.seen[0][1].content
    assert mine == kept == {"text": "My own words.", "version": 2, "by": "you"}
    assert cleared == {"text": None}
    assert none_left == {"text": None}
