# ruff: noqa: E402
"""Web tests: the person's answer on a connector card the conversation offered (decision 0046)."""

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from coscribe.conversation import ChatSessionLG, OfferLog
from coscribe.runtime_lg import mcp as lg_mcp

from .helpers import FakeToolCallingChatModel, _client_lg


class _Connection:
    async def close(self) -> None:
        pass


async def _connects(
    name: str, config: Any, *args: Any, **kwargs: Any
) -> tuple[list[Any], Any, None]:
    from coscribe.runtime import tool_metadata

    def search(query: str = "") -> str:
        """fake"""
        return query

    search.__name__ = f"{name}__search"
    return (
        [tool_metadata(search, risk_category="READ", category=f"mcp:{name}")],
        _Connection(),
        None,
    )


@pytest.fixture
def told(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(ChatSessionLG, "tell", lambda self, key, text: calls.append((key, text)))
    return calls


def _start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    return _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[]))


_MSLEARN = {"name": "mslearn", "server_url": "https://learn.microsoft.com/api/mcp"}


def test_connecting_an_offered_connector_in_settings_wakes_the_conversation_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, told: list[tuple[str, str]]
) -> None:
    with _start(tmp_path, monkeypatch) as client:
        log = OfferLog(tmp_path / "state")
        log.mark("t1", "mslearn", "offered")
        log.mark("t2", "mslearn", "declined")
        monkeypatch.setattr(lg_mcp, "connect_one_mcp_server_lg", _connects)
        assert client.post("/api/mcp/servers", json=_MSLEARN).json()["connected"] is True
        client.post("/api/mcp/servers/mslearn/reconnect", json={})

    assert [key for key, _ in told] == ["connector:mslearn"]
    assert "connected Microsoft Learn, which you offered" in told[0][1]
    assert log.state("t1", "mslearn") == "connected"
    assert log.state("t2", "mslearn") == "declined"


def test_a_connector_nobody_offered_or_that_did_not_connect_wakes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, told: list[tuple[str, str]]
) -> None:
    with _start(tmp_path, monkeypatch) as client:
        OfferLog(tmp_path / "state").mark("t1", "notion", "offered")
        client.post("/api/mcp/servers", json=_MSLEARN)
        monkeypatch.setattr(lg_mcp, "connect_one_mcp_server_lg", _connects)
        client.post("/api/mcp/servers", json=_MSLEARN)

    assert told == []
    assert OfferLog(tmp_path / "state").state("t1", "notion") == "offered"


def test_not_now_is_remembered_only_for_an_offer_made_in_that_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, told: list[tuple[str, str]]
) -> None:
    with _start(tmp_path, monkeypatch) as client:
        log = OfferLog(tmp_path / "state")
        log.mark("t1", "notion", "offered")
        declined = client.post("/api/threads/t1/connector-offers/notion/decline").json()
        elsewhere = client.post("/api/threads/t2/connector-offers/notion/decline").json()

    assert declined == {"declined": True}
    assert elsewhere == {"declined": False}
    assert log.state("t1", "notion") == "declined"
    assert log.state("t2", "notion") is None
