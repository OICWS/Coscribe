# ruff: noqa: E402
"""Web tests: Edit environment > Scripts, the machine's isolation check and a conversation's
choice to run scripts without it."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.runtime_lg import AuditLog

from .helpers import FakeToolCallingChatModel, _client_lg


@pytest.mark.skipif(sys.platform == "win32", reason="the answer off Windows")
def test_the_check_says_unsupported_off_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        status = client.get("/api/script-isolation").json()
        retest = client.post("/api/script-isolation/test").json()
    assert status["state"] == retest["state"] == "unsupported"


def test_running_without_isolation_is_per_conversation_and_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        before = client.get("/api/threads/t1/scripts").json()
        on = client.put("/api/threads/t1/scripts", json={"unisolated": True}).json()
        again = client.put("/api/threads/t1/scripts", json={"unisolated": True}).json()
        other = client.get("/api/threads/t2/scripts").json()
        off = client.put("/api/threads/t1/scripts", json={"unisolated": False}).json()
    assert before == {"unisolated": False}
    assert on == again == {"unisolated": True}
    assert other == {"unisolated": False}
    assert off == {"unisolated": False}
    entries = AuditLog(tmp_path / "state").read_all()
    assert [(e.thread_id, e.tool_name, e.decision) for e in entries] == [
        ("t1", "run_scripts_without_isolation", "approve"),
        ("t1", "run_scripts_without_isolation", "reject"),
    ]
