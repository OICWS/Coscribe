# ruff: noqa: E402
"""Web tests: the design-system library routes."""

from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from .helpers import FakeToolCallingChatModel, _client_lg


def test_a_system_is_made_edited_listed_and_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        assert client.get("/api/design-systems").json() == []
        made = client.post("/api/design-systems", json={"name": "Acme"}).json()
        assert made["name"] == "Acme"

        edited = client.put(
            f"/api/design-systems/{made['id']}", json={**made, "overview": "Calm."}
        ).json()
        assert edited["overview"] == "Calm."
        assert client.get(f"/api/design-systems/{made['id']}").json() == edited
        assert [s["name"] for s in client.get("/api/design-systems").json()] == ["Acme"]

        assert client.delete(f"/api/design-systems/{made['id']}").json() == {"status": "ok"}
        assert client.get(f"/api/design-systems/{made['id']}").status_code == 404
        assert client.delete(f"/api/design-systems/{made['id']}").status_code == 404


def test_a_bad_save_says_why_and_a_bad_id_is_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        made = client.post("/api/design-systems", json={"name": "Acme"}).json()
        bad = client.put(
            f"/api/design-systems/{made['id']}",
            json={**made, "colors": [{"name": "x", "value": "blue", "note": ""}]},
        )
        assert bad.status_code == 400 and "not a color" in bad.json()["detail"]
        assert client.post("/api/design-systems", json={"name": " "}).status_code == 400
        assert client.get("/api/design-systems/not-an-id").status_code == 404
        assert client.put("/api/design-systems/aaaaaaaaaa", json={"name": "x"}).status_code == 404
