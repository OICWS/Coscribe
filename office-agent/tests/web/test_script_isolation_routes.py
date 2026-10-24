# ruff: noqa: E402
"""Web tests: the machine's isolation check and Settings › Capabilities, and what an environment
may reach: its network, its switches and running scripts without isolation."""

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


def test_what_an_environment_may_reach_is_checked_and_each_change_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        made = client.post("/api/environments", json={"name": "Web"}).json()
        url = f"/api/environments/{made['id']}"
        limited = client.put(
            url,
            json={
                "network": {
                    "mode": "limited",
                    "domains": ["https://www.Example.com/a", "*.wiki.org", ""],
                }
            },
        ).json()
        bad = client.put(url, json={"network": {"mode": "limited", "domains": ["a b"]}})
        empty = client.put(url, json={"network": {"mode": "limited", "domains": []}})
        unisolated = client.put(url, json={"unisolated": True}).json()
        renamed = client.put(url, json={"name": "Web pages"}).json()
        not_a_switch = client.put(url, json={"commands": "yes"})
    assert made["network"] == {"mode": "limited", "domains": ["*"]}
    assert made["scripts"] is made["commands"] is True and made["unisolated"] is False
    assert limited["network"] == {"mode": "limited", "domains": ["example.com", "wiki.org"]}
    assert bad.status_code == empty.status_code == not_a_switch.status_code == 422
    assert unisolated["unisolated"] is True and renamed["name"] == "Web pages"
    entries = AuditLog(tmp_path / "state").read_all()
    created = ["commands", "environment", "name", "network", "scripts", "unisolated"]
    assert [(e.tool_name, sorted(e.arguments)) for e in entries] == [
        ("set_environment", created),
        ("set_environment", ["environment", "name", "network"]),
        ("set_environment", ["environment", "name", "unisolated"]),
    ]


def test_capabilities_change_only_by_name_and_each_change_is_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        before = client.get("/api/capabilities").json()
        on = client.put("/api/capabilities/commands", json={"on": True}).json()
        again = client.put("/api/capabilities/commands", json={"on": True}).json()
        unknown = client.put("/api/capabilities/everything", json={"on": True})
        off = client.put("/api/capabilities/commands", json={"on": False}).json()
    assert before == off == {"scripts": True, "commands": False}
    assert on == again == {"scripts": True, "commands": True}
    assert unknown.status_code == 404
    entries = AuditLog(tmp_path / "state").read_all()
    assert [(e.tool_name, e.decision) for e in entries] == [
        ("capability_commands", "approve"),
        ("capability_commands", "reject"),
    ]
