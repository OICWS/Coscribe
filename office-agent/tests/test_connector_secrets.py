"""Connectors that refer to a secret from Settings > Secrets instead of holding
a key: `{{secret:NAME}}` in a header or an env value is filled in when the
connector connects, and only for a host the secret is allowed for."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import keyring.errors
import pytest

from coscribe.runtime import SecretError, SecretStore, redactor, secrets
from coscribe.runtime_lg import mcp as lg_mcp
from coscribe.tools.mcp import (
    load_mcp_server_configs,
    prepare_for_connect,
    validate_mcp_config,
    with_secrets,
)

from .web.helpers import FakeToolCallingChatModel, _client_lg

KEY = "sk-connector-abcdef123456"


class _FakeKeyring:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}
        self.errors = keyring.errors

    def set_password(self, service: str, ref: str, value: str) -> None:
        self.store[(service, ref)] = value

    def get_password(self, service: str, ref: str) -> str | None:
        return self.store.get((service, ref))

    def delete_password(self, service: str, ref: str) -> None:
        self.store.pop((service, ref), None)


@pytest.fixture(autouse=True)
def keychain(monkeypatch: pytest.MonkeyPatch) -> _FakeKeyring:
    fake = _FakeKeyring()
    monkeypatch.setattr(secrets, "keyring", fake)
    monkeypatch.setattr(secrets, "keychain_backend_usable", lambda: True)
    return fake


def _remote(headers: dict[str, str], url: str = "https://mcp.example.com/mcp") -> Any:
    return validate_mcp_config(
        {"type": "mcp", "name": "svc", "server_url": url, "headers": headers}
    )


def test_a_header_gets_the_secret_for_the_connectors_own_host(tmp_path: Path) -> None:
    SecretStore(tmp_path).save("SVC_KEY", KEY, ["mcp.example.com"])

    config = with_secrets(_remote({"Authorization": "Bearer {{secret:SVC_KEY}}"}), tmp_path)

    assert config["headers"] == {"Authorization": f"Bearer {KEY}"}


@pytest.mark.parametrize(
    ("hosts", "url"),
    [
        (["other.example.com"], "https://mcp.example.com/mcp"),
        (["example.com"], "https://mcp.example.com/mcp"),
        (["mcp.example.com"], "https://mcp.example.com.evil.net/mcp"),
    ],
)
def test_a_header_is_refused_a_secret_that_is_not_for_that_host(
    hosts: list[str], url: str, tmp_path: Path
) -> None:
    SecretStore(tmp_path).save("SVC_KEY", KEY, hosts)

    with pytest.raises(SecretError, match="SVC_KEY") as caught:
        with_secrets(_remote({"Authorization": "{{secret:SVC_KEY}}"}, url), tmp_path)

    assert KEY not in str(caught.value) and "svc" in str(caught.value)


def test_an_env_value_for_a_local_command_gets_the_secret_without_a_host_check(
    tmp_path: Path,
) -> None:
    SecretStore(tmp_path).save("SVC_KEY", KEY, ["api.example.com"])
    config = validate_mcp_config(
        {"type": "mcp", "name": "local", "command": "npx", "env": {"TOKEN": "{{secret:SVC_KEY}}"}}
    )

    assert with_secrets(config, tmp_path)["env"] == {"TOKEN": KEY}


@pytest.mark.parametrize("state", ["none", "unknown", "missing"])
def test_a_secret_that_cannot_be_found_is_an_error_naming_it(
    state: str, tmp_path: Path, keychain: _FakeKeyring
) -> None:
    if state != "unknown":
        SecretStore(tmp_path).save("SVC_KEY", KEY, ["mcp.example.com"])
    if state == "missing":
        keychain.store.clear()
    config = _remote({"A": "{{secret:SVC_KEY}}"})

    with pytest.raises(SecretError, match="SVC_KEY|secret"):
        with_secrets(config, None if state == "none" else tmp_path)


def test_one_connectors_missing_secret_leaves_the_others_loaded(tmp_path: Path) -> None:
    SecretStore(tmp_path).save("SVC_KEY", KEY, ["mcp.example.com"])
    path = tmp_path / "mcp.json"
    path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "good": {
                        "server_url": "https://mcp.example.com/mcp",
                        "headers": {"A": "{{secret:SVC_KEY}}"},
                    },
                    "broken": {
                        "server_url": "https://mcp.example.com/mcp",
                        "headers": {"A": "{{secret:NOPE}}"},
                    },
                    "plain": {"command": "npx", "env": {"B": "literal"}},
                }
            }
        )
    )

    loaded = load_mcp_server_configs(path, tmp_path)
    shown = load_mcp_server_configs(path, tmp_path, fill_secrets=False)

    assert set(loaded) == {"good", "plain"}
    assert loaded["good"]["headers"] == {"A": KEY}
    assert shown["broken"]["headers"] == {"A": "{{secret:NOPE}}"}


def test_a_stored_keychain_reference_and_a_placeholder_are_both_read_back(
    tmp_path: Path,
) -> None:
    SecretStore(tmp_path).save("SVC_KEY", KEY, ["mcp.example.com"])
    stored = secrets.store_secret("mcp:svc:headers:A", "Bearer {{secret:SVC_KEY}}")
    config = _remote({})
    config["headers"] = {"A": stored, "B": "plain"}  # type: ignore[dict-item]

    prepared = prepare_for_connect(config, tmp_path)

    assert prepared["headers"] == {"A": f"Bearer {KEY}", "B": "plain"}


def test_through_the_api_the_value_is_never_stored_shown_or_deleted_while_in_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    seen: list[Any] = []

    async def recording_connect(name: str, config: Any, *args: Any, **kwargs: Any) -> Any:
        seen.append(config)
        return [], None, None

    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        monkeypatch.setattr(lg_mcp, "connect_one_mcp_server_lg", recording_connect)
        client.put("/api/secrets/SVC_KEY", json={"value": KEY, "hosts": ["mcp.example.com"]})
        wrong_host = client.post(
            "/api/mcp/servers",
            json={
                "name": "bad",
                "server_url": "https://elsewhere.example.net/mcp",
                "headers": {"Authorization": "Bearer {{secret:SVC_KEY}}"},
            },
        )
        added = client.post(
            "/api/mcp/servers",
            json={
                "name": "svc",
                "server_url": "https://mcp.example.com/mcp",
                "headers": {"Authorization": "Bearer {{secret:SVC_KEY}}"},
            },
        )
        listed = client.get("/api/mcp/servers")
        refused = client.delete("/api/secrets/SVC_KEY")
        removed = client.delete("/api/mcp/servers/svc")
        deleted = client.delete("/api/secrets/SVC_KEY")

    assert "SVC_KEY" in wrong_host.json()["rejected"]["bad"]
    assert added.json()["rejected"] == {}
    assert [c["headers"] for c in seen] == [{"Authorization": f"Bearer {KEY}"}]
    saved = (tmp_path / "mcp.json").read_text()
    assert KEY not in saved

    shown = listed.json()["svc"]["masked_headers"]["Authorization"]
    assert "{{secret:SVC_KEY}}" in shown and KEY not in shown and KEY[-4:] not in shown
    assert refused.status_code == 409 and refused.json()["connectors"] == ["svc"]
    assert removed.status_code == 200
    assert deleted.status_code == 200


def test_a_secrets_value_that_looks_like_a_placeholder_is_not_expanded_again(
    tmp_path: Path,
) -> None:
    store = SecretStore(tmp_path)
    store.save("INNER_KEY", "inner-secret-value", ["mcp.example.com"])
    store.save("OUTER_KEY", "x{{secret:INNER_KEY}}y-padding", ["mcp.example.com"])

    config = with_secrets(_remote({"A": "{{secret:OUTER_KEY}}"}), tmp_path)

    assert config["headers"] == {"A": "x{{secret:INNER_KEY}}y-padding"}


def test_the_connector_list_says_why_a_connector_has_no_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    (tmp_path / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "svc": {
                        "server_url": "https://mcp.example.com/mcp",
                        "headers": {"A": "{{secret:NOPE}}"},
                    },
                    "ok": {"server_url": "https://mcp.example.com/mcp", "headers": {"A": "x"}},
                }
            }
        )
    )
    with _client_lg(
        tmp_path,
        monkeypatch,
        FakeToolCallingChatModel(responses=[]),
        mcp_config_path=tmp_path / "mcp.json",
    ) as client:
        listed = client.get("/api/mcp/servers").json()

    assert "NOPE" in listed["svc"]["secret_error"]
    assert listed["ok"]["secret_error"] is None


def test_an_unreadable_connector_setting_blocks_deleting_a_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, keychain: _FakeKeyring
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    stored = secrets.store_secret("mcp:svc:headers:A", "Bearer {{secret:SVC_KEY}}")
    (tmp_path / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "svc": {
                        "server_url": "https://mcp.example.com/mcp",
                        "headers": {"A": stored},
                    }
                }
            }
        )
    )
    with _client_lg(
        tmp_path,
        monkeypatch,
        FakeToolCallingChatModel(responses=[]),
        mcp_config_path=tmp_path / "mcp.json",
    ) as client:
        client.put("/api/secrets/SVC_KEY", json={"value": KEY, "hosts": ["mcp.example.com"]})
        for key in [k for k in keychain.store if k[1].startswith("mcp:")]:
            del keychain.store[key]
        blocked = client.delete("/api/secrets/SVC_KEY")

    assert blocked.status_code == 503
    assert SecretStore(tmp_path / "state").names() == {"SVC_KEY"}


def test_a_keychain_value_that_cannot_be_read_skips_that_connector_only(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    path = tmp_path / "mcp.json"
    path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "gone": {
                        "command": "npx",
                        "env": {"TOKEN": {"keyring_ref": "mcp-gone-token"}},
                    },
                    "plain": {"command": "npx", "env": {"B": "literal"}},
                }
            }
        )
    )

    loaded = load_mcp_server_configs(path, tmp_path)
    listed = load_mcp_server_configs(path, tmp_path, fill_secrets=False)

    assert set(loaded) == {"plain"}
    assert set(listed) == {"gone", "plain"}
    assert listed["gone"]["env"] == {"TOKEN": ""}


def test_a_key_typed_into_a_connector_is_blanked_once_it_connects(tmp_path: Path) -> None:
    typed = "typed-env-key-9m4n1x8w"
    local = validate_mcp_config(
        {"type": "mcp", "name": "local", "command": "npx", "env": {"TOKEN": typed}}
    )
    remote = _remote({"Authorization": "Bearer hdr-token-5q7w2e9r"})

    prepare_for_connect(local, tmp_path)
    prepare_for_connect(remote, tmp_path)

    blank = redactor(tmp_path)
    assert typed not in blank(f"the server says {typed}")
    assert "hdr-token-5q7w2e9r" not in blank("echoed hdr-token-5q7w2e9r alone")
    assert blank("ordinary text") == "ordinary text"


def test_a_key_typed_into_a_connector_is_blanked_when_the_app_starts(tmp_path: Path) -> None:
    typed = "typed-env-key-9m4n1x8w"
    config = tmp_path / "mcp.json"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "local": {"command": "npx", "env": {"TOKEN": typed, "MODE": "production"}}
                }
            }
        ),
        encoding="utf-8",
    )

    load_mcp_server_configs(config, tmp_path)

    assert redactor(tmp_path)(f"TOKEN={typed} MODE=production") == (
        "TOKEN=[REDACTED SECRET] MODE=production"
    )


def test_a_connector_setting_that_is_not_a_credential_stays_readable(tmp_path: Path) -> None:
    settings = {
        "NODE_ENV": "production",
        "ALLOWED_DIR": "C:\\Users\\someone\\Documents",
        "API_BASE": "https://api.example.com/v2",
        "PATH": "/usr/local/bin:/usr/bin",
    }
    odd_name = "a1b2c3d4e5f6g7h8i9j0k1l2"
    local = validate_mcp_config(
        {"type": "mcp", "name": "local", "command": "npx", "env": {**settings, "GH": odd_name}}
    )
    remote = _remote(
        {
            "Content-Type": "application/json",
            "X-Api-Version": "2024-01-01",
            "X-Api-Key": "k3y-9f8e7d6c",
        }
    )

    prepare_for_connect(local, tmp_path)
    prepare_for_connect(remote, tmp_path)

    blank = redactor(tmp_path)
    for value in [*settings.values(), "application/json", "2024-01-01"]:
        assert blank(f"read {value} back") == f"read {value} back"
    assert odd_name not in blank(f"echoed {odd_name}")
    assert "k3y-9f8e7d6c" not in blank("echoed k3y-9f8e7d6c")


def test_a_connectors_sign_in_tokens_are_blanked(tmp_path: Path) -> None:
    from mcp.shared.auth import OAuthToken

    from coscribe.runtime_lg import McpOAuth

    storage = McpOAuth(tmp_path)._storage("docs")
    asyncio.run(
        storage.set_tokens(
            OAuthToken(access_token="oauth-access-3k8d1f6g", refresh_token="oauth-refresh-2h5j7l")
        )
    )

    text = redactor(tmp_path)("token oauth-access-3k8d1f6g and oauth-refresh-2h5j7l")
    assert "oauth-access" not in text and "oauth-refresh" not in text


def test_a_refreshed_sign_in_keeps_the_previous_token_blanked(tmp_path: Path) -> None:
    from mcp.shared.auth import OAuthToken

    from coscribe.runtime_lg import McpOAuth

    storage = McpOAuth(tmp_path)._storage("docs")
    asyncio.run(storage.set_tokens(OAuthToken(access_token="first-access-4r6t8y0u")))
    asyncio.run(storage.set_tokens(OAuthToken(access_token="second-access-1q3w5e7r")))

    text = redactor(tmp_path)("first-access-4r6t8y0u then second-access-1q3w5e7r")
    assert "first-access" not in text and "second-access" not in text


def _connect_local(tmp_path: Path, **fields: Any) -> None:
    prepare_for_connect(
        validate_mcp_config({"type": "mcp", "name": "local", "command": "npx", **fields}), tmp_path
    )


def test_a_password_in_a_connection_string_is_blanked_and_the_rest_stays(tmp_path: Path) -> None:
    _connect_local(tmp_path, env={"DATABASE_URL": "postgres://app:hunter2secretpw@db.local/app"})

    blank = redactor(tmp_path)
    assert blank("could not connect to postgres://app:hunter2secretpw@db.local/app") == (
        "could not connect to postgres://[REDACTED SECRET]@db.local/app"
    )
    assert blank('password hunter2secretpw for user "app"') == (
        'password [REDACTED SECRET] for user "app"'
    )


def test_a_short_password_is_blanked_with_its_user_name(tmp_path: Path) -> None:
    _connect_local(tmp_path, env={"DB": "mysql://admin:pw12@db.local:3306/shop"})

    text = redactor(tmp_path)("dsn mysql://admin:pw12@db.local:3306/shop failed")
    assert "pw12" not in text and "db.local:3306/shop" in text


def test_a_percent_encoded_password_is_blanked_as_written_and_decoded(tmp_path: Path) -> None:
    _connect_local(
        tmp_path, env={"MONGO": "mongodb://app:s3cr%40t-pass-1@h1,h2/db?authSource=admin"}
    )

    blank = redactor(tmp_path)
    assert "s3cr%40t-pass-1" not in blank("uri mongodb://app:s3cr%40t-pass-1@h1,h2/db")
    assert "s3cr@t-pass-1" not in blank("password s3cr@t-pass-1 rejected")
    assert blank("authSource=admin on h1,h2") == "authSource=admin on h1,h2"


def test_a_connection_string_in_the_command_line_is_blanked(tmp_path: Path) -> None:
    _connect_local(
        tmp_path,
        args=[
            "-y",
            "@modelcontextprotocol/server-postgres",
            "postgresql://app:arg-pass-7k2m@db/app",
        ],
    )

    assert "arg-pass-7k2m" not in redactor(tmp_path)("connecting with arg-pass-7k2m")


def test_a_token_used_as_the_user_name_of_a_url_is_blanked(tmp_path: Path) -> None:
    token = "ghp_a1B2c3D4e5F6g7H8i9J0k1L2"
    _connect_local(tmp_path, env={"REPO": f"https://{token}@github.com/acme/app.git"})

    assert redactor(tmp_path)(f"clone https://{token}@github.com/acme/app.git") == (
        "clone https://[REDACTED SECRET]@github.com/acme/app.git"
    )


def test_a_credential_named_part_of_a_connection_string_is_blanked(tmp_path: Path) -> None:
    _connect_local(
        tmp_path,
        env={"SQL": "Server=db.local;Database=shop;User Id=app;Password=Ado-Pass-9x;Encrypt=true"},
        args=["--db-password=flag-pass-4h6j", "--api-token", "split-flag-tok-8"],
    )
    prepare_for_connect(
        _remote({}, url="https://mcp.example.com/sse?api_key=query-key-5t1u"), tmp_path
    )

    blank = redactor(tmp_path)
    for secret in ("Ado-Pass-9x", "flag-pass-4h6j", "split-flag-tok-8", "query-key-5t1u"):
        assert secret not in blank(f"echoed {secret}")
    assert blank("Server=db.local;Database=shop;User Id=app") == (
        "Server=db.local;Database=shop;User Id=app"
    )


def test_a_url_without_credentials_stays_readable(tmp_path: Path) -> None:
    plain = [
        "https://api.example.com/v2?version=2024-01-01&mode=production",
        "postgres://db.local:5432/app?sslmode=require&sslkey=/home/app/client.key",
        "https://someone@example.com/profile",
    ]
    _connect_local(tmp_path, env={f"URL{i}": url for i, url in enumerate(plain)}, args=plain)

    blank = redactor(tmp_path)
    for url in plain:
        assert blank(f"read {url} back") == f"read {url} back"
