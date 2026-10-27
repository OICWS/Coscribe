# ruff: noqa: E402
"""Web tests: settings, providers, secrets, environment packages and permissions."""

import json
import os
import shutil
import socket
import stat
import sys
from pathlib import Path
from typing import Any

import keyring.errors
import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from dotenv import dotenv_values
from langchain_core.messages import (
    AIMessage,
)
from langchain_core.messages.ai import UsageMetadata

from coscribe.conversation import session as conversation_session
from coscribe.runtime import secrets as secrets_module
from coscribe.web.routes.settings import proxy as settings_proxy_routes

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _install_fake_keyring,
    _receive_until,
)


def test_usage_event_includes_cache_stats_when_the_provider_reports_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real, user-reported gap: the token counter only ever showed a
    running total_tokens, with no way to tell whether prompt caching was
    actually reducing anything -- a long, tool-heavy conversation looks
    identical either way from that one number alone. langchain-core's
    standard `input_token_details.cache_read` field (populated for
    Anthropic's own explicit cache_control breakpoints, and, unprompted
    by any coscribe code, by langchain_openai for any OpenAI-compatible
    provider that reports its own `prompt_tokens_details.cached_tokens`
    -- GLM's documented "implicit caching" is exactly this shape) is now
    surfaced in the "usage" event as cache_read_tokens/input_tokens/
    cache_hit_rate. See test_usage_event_sent_when_the_model_reports_
    usage_metadata right above for the *absence* case (no
    input_token_details at all) -- this proves the *presence* case,
    including the exact hit-rate arithmetic."""
    fake_model = FakeToolCallingChatModel(
        responses=[
            AIMessage(
                content="hi there!",
                usage_metadata=UsageMetadata(
                    input_tokens=1000,
                    output_tokens=50,
                    total_tokens=1050,
                    input_token_details={"cache_read": 800},
                ),
            )
        ]
    )
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_usage_cache") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "user_message", "text": "hello"})
            messages = _receive_until(ws, "tasks_changed")

    usage_message = next(m for m in messages if m["type"] == "usage")
    assert usage_message == {
        "type": "usage",
        "total_tokens": 1050,
        "cache_read_tokens": 800,
        "input_tokens": 1000,
        "cache_hit_rate": 0.8,
    }


def test_switch_model_rejects_a_string_without_a_provider_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        with client.websocket_connect("/ws/t_switch2") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history
            ws.send_json({"type": "switch_model", "model": "no-colon-here"})
            error = ws.receive_json()

    assert error["type"] == "error"
    assert "provider:model" in error["message"]


def test_switch_model_picks_up_a_provider_added_after_the_session_was_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real, live-reported bug: self._custom_providers used to only ever be
    loaded once, when a thread's ChatSessionLG was first created (see
    _get_session in web/app.py) -- adding a custom provider via the
    Providers tab while that thread was already open was invisible to it,
    so switch_model would raise resolve_chat_model's own "Unsupported
    provider" even though the provider genuinely was just configured.
    switch_model now reloads providers.json fresh on every switch instead
    of trusting that startup-time snapshot."""
    # chdir first -- add_provider's fallback path (no providers_config_path
    # configured yet) is a bare relative "./providers.json", resolved
    # against cwd (see test_post_provider_persists_an_absolute_path_not_a_
    # cwd_relative_one's own docstring for why this matters: skipping it
    # writes a real file into the repo root instead of tmp_path).
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    seen_custom_providers: list[dict[str, dict[str, str]] | None] = []

    def _fake_resolve(model: str, custom_providers: dict[str, dict[str, str]] | None = None) -> Any:
        seen_custom_providers.append(custom_providers)
        return fake_model

    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        # Must be set *after* entering _client_lg -- see the identical
        # gotcha noted on test_switch_model_rebuilds_the_graph above.
        monkeypatch.setattr(conversation_session, "resolve_chat_model", _fake_resolve)
        with client.websocket_connect("/ws/t_switch_new_provider") as ws:
            ws.receive_json()  # state
            ws.receive_json()  # history -- session object created here, no custom providers yet

            response = client.post(
                "/api/providers",
                json={
                    "name": "deepseek",
                    "base_url": "https://api.deepseek.com/v1",
                    "api_key": "sk-test",
                },
            )
            assert response.status_code == 200

            ws.send_json({"type": "switch_model", "model": "deepseek:deepseek-flash"})
            switched_state = ws.receive_json()
            assert switched_state["type"] == "state"
            assert switched_state["model"] == "deepseek:deepseek-flash"

    assert seen_custom_providers[-1] is not None
    assert seen_custom_providers[-1].get("deepseek") == {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "sk-test",
    }


# -- /api/config, /api/mcp/*, /api/providers/* -- see app.py's module
# docstring for the one behavioral difference from web/app.py's identical
# endpoints: a change here applies to the *next new* session, not every
# already-open one (runtime_lg's compiled graph can't be hot-mutated the
# way the old runtime's per-turn tool/model resolution can).


def test_get_config_masks_provider_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=sk-1234567890abcdef\n", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/config")

    assert response.status_code == 200
    body = response.json()
    assert body["GEMINI_API_KEY"]["set"] is True
    assert body["GEMINI_API_KEY"]["masked"] != "sk-1234567890abcdef"
    assert body["GEMINI_API_KEY"]["masked"].endswith("cdef")


def test_post_config_updates_env_and_rejects_bad_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This endpoint sets os.environ["GEMINI_API_KEY"] directly (mirroring
    # web/app.py's identical update_config) -- monkeypatch can't auto-clean
    # that up for later tests since it wasn't the one that set it. Not
    # order-*dependent* the way the MCP-config-path test is (this always
    # runs unconditionally, no "only if unset" branch to skip), but
    # asserting the exact value written is only meaningful starting from a
    # known-clean slate.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/config",
            json={
                "updates": {
                    "GEMINI_API_KEY": "sk-newkey",
                    "COSCRIBE_DEFAULT_MODEL": "no-colon-here",
                }
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["rejected"] == {
        "COSCRIBE_DEFAULT_MODEL": ('must be a "provider:model" string, e.g. "anthropic:sonnet"')
    }
    # A machine with a working keychain stores a reference, not the value.
    stored = dotenv_values(tmp_path / ".env")["GEMINI_API_KEY"]
    assert stored in ("sk-newkey", "__coscribe_keyring__:builtin-provider:GEMINI_API_KEY")
    assert os.environ["GEMINI_API_KEY"] == "sk-newkey"


def test_get_config_includes_background_on_close_desktop_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """COSCRIBE_BACKGROUND_ON_CLOSE is Rust-consumed (office-agent-desktop's
    lib.rs reads the same .env file directly, see DESKTOP_ENV_VARS's own
    comment) -- this Python process never branches on it, but /api/config
    still has to surface it for the Settings panel's toggle to read/write,
    same as every other desktop-facing value that lives in this file."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("COSCRIBE_BACKGROUND_ON_CLOSE=false\n", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["COSCRIBE_BACKGROUND_ON_CLOSE"] == "false"


def test_post_config_can_set_background_on_close_without_requiring_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unlike every COSCRIBE_ENV_VARS entry, this one must NOT mark
    restart_required -- the Rust shell re-reads .env live at the next
    window close, no coscribe-web restart needed (see DESKTOP_ENV_VARS's
    own comment for why it's a separate list from COSCRIBE_ENV_VARS)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/config", json={"updates": {"COSCRIBE_BACKGROUND_ON_CLOSE": "false"}}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["rejected"] == {}
    assert body["restart_required"] is False
    assert dotenv_values(tmp_path / ".env")["COSCRIBE_BACKGROUND_ON_CLOSE"] == "false"


def test_post_config_saves_the_desktop_session_settings_without_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    updates = {
        "COSCRIBE_FLASH_ON_ATTENTION": "false",
        "COSCRIBE_KEEP_AWAKE": "false",
        "COSCRIBE_KEEP_AWAKE_ON_BATTERY": "false",
    }
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post("/api/config", json={"updates": updates})
        shown = client.get("/api/config").json()

    assert response.json() == {"restart_required": False, "rejected": {}}
    assert {key: shown[key] for key in updates} == updates


def test_get_and_post_memory_round_trip_the_global_instructions_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET/POST /api/memory back the Settings panel's Global Instructions
    editor (GeneralTab.tsx's GlobalInstructionsSection) -- a direct
    read/overwrite of MEMORY.md's content, the only way it is written."""
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        empty = client.get("/api/memory")
        assert empty.status_code == 200
        assert empty.json() == {"content": ""}

        posted = client.post("/api/memory", json={"content": "- prefers concise replies"})
        assert posted.status_code == 200
        assert posted.json() == {"status": "ok"}

        refreshed = client.get("/api/memory")
        assert refreshed.json() == {"content": "- prefers concise replies"}

    assert (tmp_path / "MEMORY.md").read_text(encoding="utf-8") == "- prefers concise replies"


def test_post_and_delete_provider_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/providers",
            json={
                "name": "deepseek",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "sk-deepseek",
            },
        )
        assert response.status_code == 200
        assert response.json() == {"restart_required": False, "rejected": {}}

        providers = client.get("/api/providers").json()
        assert providers["deepseek"]["base_url"] == "https://api.deepseek.com/v1"
        assert providers["deepseek"]["masked_key"].endswith("eek")

        response = client.delete("/api/providers/deepseek")
        assert response.status_code == 200

        providers = client.get("/api/providers").json()
        assert "deepseek" not in providers


def test_get_providers_falls_back_to_the_global_default_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real bug, live-reported: a fresh install's COSCRIBE_GEMINI_DEFAULT_
    MODEL was never written (see test_setup_app.py's own fix note), so
    get_providers used to report an empty default_model for gemini even
    though it's the app's own active default provider -- ModelPicker.tsx
    filters out any entry with a blank default_model, so gemini would
    silently vanish from the switcher's dropdown the moment the user
    switched to a second, properly-configured provider and tried to
    switch back. Fixed by falling back to COSCRIBE_DEFAULT_MODEL's own
    model portion when the per-provider var is unset but that global
    default names this same provider."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY='test-gemini-key'\nCOSCRIBE_DEFAULT_MODEL='gemini:gemini-flash-latest'\n",
        encoding="utf-8",
    )
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        providers = client.get("/api/providers").json()
        assert providers["gemini"]["default_model"] == "gemini-flash-latest"


def test_get_providers_prefers_the_per_provider_default_model_when_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY='test-gemini-key'\n"
        "COSCRIBE_DEFAULT_MODEL='anthropic:claude-opus-5'\n"
        "COSCRIBE_GEMINI_DEFAULT_MODEL='gemini-2.5-pro'\n"
        "ANTHROPIC_API_KEY='sk-ant-test'\n",
        encoding="utf-8",
    )
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        providers = client.get("/api/providers").json()
        assert providers["gemini"]["default_model"] == "gemini-2.5-pro"


def test_post_provider_persists_an_absolute_path_not_a_cwd_relative_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real bug, not hypothetical: add_provider's fallback path used to be
    a bare relative Path("./providers.json"), persisted verbatim into both
    settings.providers_config_path and .env. That's fine for the rest of
    *this* process's life only as long as cwd never changes again -- which
    it does, routinely, between test functions and (for a real deployment)
    between process restarts from a different working directory. Confirmed
    live: a real .env left over from an earlier manual run, holding that
    relative value, made an unrelated batch of tests fail with
    FileNotFoundError purely because they didn't all chdir the same way as
    the test that wrote it. Asserting the persisted value is absolute is
    what actually pins the fix -- a relative-but-different-looking string
    would pass a weaker "is not exactly 'providers.json'" check."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/providers",
            json={
                "name": "glm",
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key": "sk-glm",
            },
        )
        assert response.status_code == 200

    persisted = dotenv_values(tmp_path / ".env")["COSCRIBE_PROVIDERS_CONFIG_PATH"]
    assert persisted is not None
    assert Path(persisted).is_absolute()
    assert Path(persisted) == tmp_path / "providers.json"


def test_post_provider_stores_via_keyring_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_keyring = _install_fake_keyring(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        client.post(
            "/api/providers",
            json={
                "name": "deepseek",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "sk-deepseek-real",
            },
        )

        raw = json.loads((tmp_path / "providers.json").read_text(encoding="utf-8"))
        assert raw["providers"]["deepseek"]["api_key"] == {
            "keyring_ref": "custom-provider:deepseek"
        }
        assert fake_keyring.store[("coscribe", "custom-provider:deepseek")] == "sk-deepseek-real"

        # Masking still works correctly -- resolved via the keyring before
        # _mask ever sees it.
        providers = client.get("/api/providers").json()
        assert providers["deepseek"]["masked_key"].endswith("eal")

        client.delete("/api/providers/deepseek")

    assert ("coscribe", "custom-provider:deepseek") not in fake_keyring.store


def test_post_provider_builtin_key_stored_via_keyring_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_keyring = _install_fake_keyring(monkeypatch)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        client.post(
            "/api/providers",
            json={"name": "gemini", "base_url": "", "api_key": "sk-gemini-real"},
        )

        env_value = dotenv_values(tmp_path / ".env")["GEMINI_API_KEY"]
        assert env_value is not None
        assert env_value.startswith(secrets_module.ENV_KEYRING_PREFIX)
        assert "sk-gemini-real" not in env_value
        # The live process still gets the real value immediately, not the
        # sentinel -- no restart needed to use the key just entered.
        assert os.environ["GEMINI_API_KEY"] == "sk-gemini-real"

        providers = client.get("/api/providers").json()
        assert providers["gemini"]["masked_key"].endswith("eal")

    assert fake_keyring.store[("coscribe", "builtin-provider:GEMINI_API_KEY")] == "sk-gemini-real"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits")
def test_provider_files_get_owner_only_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    os.chmod(tmp_path / ".env", 0o644)
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        client.post(
            "/api/providers",
            json={
                "name": "deepseek",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "sk-deepseek",
            },
        )
        client.post(
            "/api/providers",
            json={"name": "gemini", "base_url": "", "api_key": "sk-gemini"},
        )

    assert stat.S_IMODE((tmp_path / "providers.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / ".env").stat().st_mode) == 0o600


def _network_reachable() -> bool:
    """The script-env package endpoints need pypi.org for their first real
    call (creating the venv seeds baseline packages) -- skip cleanly
    offline, same reasoning as test_script_env.py's identical helper."""
    try:
        socket.create_connection(("pypi.org", 443), timeout=5).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _network_reachable(), reason="pypi.org not reachable from this environment")
def test_script_env_package_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        # First call creates the venv and seeds baseline packages.
        baseline = client.get("/api/script-env/packages").json()
        baseline_names = {pkg["name"].lower() for pkg in baseline}
        assert "openpyxl" in baseline_names

        response = client.post("/api/script-env/packages", json={"package": "six"})
        assert response.status_code == 200
        assert response.json() == {"success": True, "error": None}

        packages = client.get("/api/script-env/packages").json()
        assert "six" in {pkg["name"].lower() for pkg in packages}

        response = client.delete("/api/script-env/packages/six")
        assert response.status_code == 200
        assert response.json()["success"] is True

        packages = client.get("/api/script-env/packages").json()
        assert "six" not in {pkg["name"].lower() for pkg in packages}


def test_post_script_env_package_rejects_blank_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post("/api/script-env/packages", json={"package": "  "})

    assert response.status_code == 200
    assert response.json()["success"] is False


def test_get_script_env_interpreter_starts_unconfigured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/script-env/interpreter")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is None
    # python and python3 are often one file; the list names it once.
    found = [os.path.realpath(python["path"]) for python in body["found"]]
    assert os.path.realpath(sys.executable) in found
    assert body["own_python"]["downloaded"] is False


def test_set_script_env_interpreter_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post("/api/script-env/interpreter", json={"path": sys.executable})
        assert response.status_code == 200
        assert response.json() == {"success": True, "error": None}

        info = client.get("/api/script-env/interpreter").json()
        assert info["configured"] == sys.executable

        cleared = client.post("/api/script-env/interpreter", json={"path": ""})
        assert cleared.json() == {"success": True, "error": None}

        info_after_clear = client.get("/api/script-env/interpreter").json()
        assert info_after_clear["configured"] is None


def test_set_script_env_interpreter_rejects_a_bad_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/script-env/interpreter", json={"path": str(tmp_path / "not-a-real-interpreter")}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"]


def _node_npm_available_and_reachable() -> bool:
    """Mirrors _network_reachable above, plus node/npm actually being
    installed -- unlike Python (coscribe's own runtime, always present),
    Node is a genuinely optional system dependency (see tools/exec/node_env.py)
    that may not exist in every CI environment."""
    if shutil.which("node") is None or shutil.which("npm") is None:
        return False
    try:
        socket.create_connection(("registry.npmjs.org", 443), timeout=5).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(
    not _node_npm_available_and_reachable(),
    reason="node/npm not installed, or registry.npmjs.org not reachable from this environment",
)
def test_node_env_package_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        # First call creates node-env and seeds pptxgenjs.
        baseline = client.get("/api/node-env/packages").json()
        baseline_names = {pkg["name"].lower() for pkg in baseline}
        assert "pptxgenjs" in baseline_names

        response = client.post("/api/node-env/packages", json={"package": "left-pad"})
        assert response.status_code == 200
        assert response.json() == {"success": True, "error": None}

        packages = client.get("/api/node-env/packages").json()
        assert "left-pad" in {pkg["name"].lower() for pkg in packages}

        response = client.delete("/api/node-env/packages/left-pad")
        assert response.status_code == 200
        assert response.json()["success"] is True

        packages = client.get("/api/node-env/packages").json()
        assert "left-pad" not in {pkg["name"].lower() for pkg in packages}


def test_post_node_env_package_rejects_blank_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post("/api/node-env/packages", json={"package": "  "})

    assert response.status_code == 200
    assert response.json()["success"] is False


def test_a_new_default_model_applies_to_the_next_session_without_a_restart_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[AIMessage(content="hi")])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/config",
            json={"updates": {"COSCRIBE_DEFAULT_MODEL": "deepseek:deepseek-pro",
                              "COSCRIBE_MAX_TURNS": "7"}},
        )  # fmt: skip
        with client.websocket_connect("/ws/t_after_default") as ws:
            state = ws.receive_json()

    assert response.json()["restart_required"] is False
    assert state["model"] == "deepseek:deepseek-pro"
    assert dotenv_values(tmp_path / ".env")["COSCRIBE_MAX_TURNS"] == "7"


def test_the_code_settings_are_checked_and_apply_live_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        bad = client.post(
            "/api/config",
            json={
                "updates": {
                    "COSCRIBE_CODE_MODEL": "deepseek-flash",
                    "COSCRIBE_CODE_MODULE_ENABLED": "yes",
                }
            },
        )
        good = client.post(
            "/api/config",
            json={
                "updates": {
                    "COSCRIBE_CODE_MODEL": "deepseek:deepseek-flash",
                    "COSCRIBE_CODE_MODULE_ENABLED": "true",
                }
            },
        )
        chosen = client.get("/api/code").json()
        client.post("/api/config", json={"updates": {"COSCRIBE_CODE_MODEL": ""}})
        default = client.get("/api/code").json()

    assert set(bad.json()["rejected"]) == {
        "COSCRIBE_CODE_MODEL",
        "COSCRIBE_CODE_MODULE_ENABLED",
    }
    assert good.json() == {"restart_required": False, "rejected": {}}
    assert chosen["model"] == "deepseek:deepseek-flash"
    assert "deepseek" in chosen["model_problem"]
    assert (chosen["installed"], chosen["preparing"]) == (False, False)
    assert default["model"] == "fake:model"


def test_code_permissions_are_stored_and_checked_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        initial = client.get("/api/code/permissions").json()
        saved = client.put("/api/code/permissions", json={"run_code_command": "allow"})
        after = client.get("/api/code/permissions").json()
        unknown = client.put("/api/code/permissions", json={"delete_everything": "allow"})
        bad = client.put("/api/code/permissions", json={"apply_code_change": "sometimes"})

    assert initial == {"run_code_command": "ask", "apply_code_change": "ask"}
    assert saved.json() == after == {"run_code_command": "allow", "apply_code_change": "ask"}
    assert unknown.status_code == bad.status_code == 422


def test_secrets_api_never_returns_a_value_and_refuses_without_a_keychain_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    kept: dict[str, str] = {}

    class _Keychain:
        errors = keyring.errors

        def set_password(self, service: str, ref: str, value: str) -> None:
            kept[ref] = value

        def get_password(self, service: str, ref: str) -> str | None:
            return kept.get(ref)

        def delete_password(self, service: str, ref: str) -> None:
            kept.pop(ref, None)

    monkeypatch.setattr(secrets_module, "keyring", _Keychain())
    usable = {"yes": True}
    monkeypatch.setattr(secrets_module, "keychain_backend_usable", lambda: usable["yes"])
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        created = client.put(
            "/api/secrets/STRIPE_KEY", json={"value": "sk-live-1", "hosts": ["api.stripe.com"]}
        )
        listed = client.get("/api/secrets")
        no_hosts = client.put("/api/secrets/OTHER", json={"value": "value-ok-1", "hosts": []})
        usable["yes"] = False
        no_keychain = client.put(
            "/api/secrets/OTHER", json={"value": "value-ok-1", "hosts": ["a.com"]}
        )
        listed_without = client.get("/api/secrets")
        usable["yes"] = True

        attached = client.post(
            "/api/environments",
            json={"name": "Billing", "variables": {"MODE": "fast"}, "secrets": ["STRIPE_KEY"]},
        )
        unknown = client.post("/api/environments", json={"name": "X", "secrets": ["NOPE"]})
        deleted = client.delete("/api/secrets/STRIPE_KEY")
        [after_delete] = [
            e
            for e in client.get("/api/environments").json()["environments"]
            if e["name"] == "Billing"
        ]
        missing = client.delete("/api/secrets/STRIPE_KEY")

    assert created.status_code == 200
    assert created.json()["hosts"] == ["api.stripe.com"]
    assert "sk-live-1" not in created.text
    assert kept == {}  # removed again by the delete below
    assert listed.json()["keychain"] is True
    assert [s["name"] for s in listed.json()["secrets"]] == ["STRIPE_KEY"]
    assert "sk-live-1" not in listed.text
    assert no_hosts.status_code == 422 and "host" in no_hosts.json()["error"]
    assert no_keychain.status_code == 503
    assert no_keychain.json()["code"] == "keychain_unavailable"
    assert listed_without.json()["keychain"] is False
    assert attached.json()["secrets"] == ["STRIPE_KEY"]
    assert unknown.status_code == 422 and "NOPE" in unknown.json()["error"]
    assert deleted.json() == {"deleted": "STRIPE_KEY"}
    assert after_delete["variables"] == {"MODE": "fast"} and after_delete["secrets"] == []
    assert missing.status_code == 404


def test_coscribe_s_own_python_downloads_only_when_asked_and_is_then_chosen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.web.routes.settings import environments

    asked: list[Path] = []

    def download(state_dir: Path) -> Path:
        asked.append(state_dir)
        return Path(sys.executable)

    monkeypatch.setattr(environments, "ensure_own_python", download)
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        client.get("/api/script-env/interpreter")
        assert asked == []
        result = client.post("/api/script-env/own-python").json()
        configured = client.get("/api/script-env/interpreter").json()["configured"]

    assert result == {"success": True, "error": None, "path": sys.executable}
    assert configured == sys.executable


def test_a_failed_own_python_download_says_why(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.web.routes.settings import environments

    def offline(state_dir: Path) -> Path:
        raise RuntimeError("Could not download Python from x: offline")

    monkeypatch.setattr(environments, "ensure_own_python", offline)
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        result = client.post("/api/script-env/own-python").json()
        configured = client.get("/api/script-env/interpreter").json()["configured"]

    assert result == {"success": False, "error": "Could not download Python from x: offline"}
    assert configured is None


def test_the_proxy_setting_starts_as_system(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        body = client.get("/api/settings/proxy").json()

    assert body["mode"] == "system"
    assert body["bypass"] == "localhost, 127.0.0.1"
    assert body["password_set"] is False


def test_a_manual_proxy_keeps_its_password_in_the_keychain_and_never_sends_it_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_keyring = _install_fake_keyring(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    manual = {
        "mode": "manual",
        "address": "proxy.corp:8080",
        "bypass": "localhost, .corp",
        "username": "alice",
        "password": "hunter2",
    }
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        saved = client.put("/api/settings/proxy", json=manual).json()
        fetched = client.get("/api/settings/proxy").text
        config = client.get("/api/config").text
        # No password sent: the saved one stays.
        client.put("/api/settings/proxy", json={**manual, "password": None})
        kept = dict(fake_keyring.store)

    env = dotenv_values(tmp_path / ".env")
    assert saved["restart_required"] is True and saved["password_set"] is True
    assert saved["address"] == "http://proxy.corp:8080" and saved["username"] == "alice"
    assert "hunter2" not in fetched and "hunter2" not in config
    assert "hunter2" not in (tmp_path / ".env").read_text(encoding="utf-8")
    assert env["HTTPS_PROXY"] == env["http_proxy"] == "__coscribe_keyring__:setting:proxy"
    assert env["NO_PROXY"] == "localhost,.corp,127.0.0.1,::1" and env["ALL_PROXY"] == ""
    assert kept[("coscribe", "setting:proxy")] == "http://alice:hunter2@proxy.corp:8080"

    # What the next start makes of it.
    monkeypatch.setattr(os, "environ", {k: v or "" for k, v in env.items()})
    secrets_module.resolve_env_keyring_refs()
    assert os.environ["HTTPS_PROXY"] == "http://alice:hunter2@proxy.corp:8080"


def test_a_saved_password_is_not_sent_to_a_different_proxy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mistyped host must not be handed the person's company credential."""
    _install_fake_keyring(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    tried: list[str | None] = []

    def fake_try(proxy: str | None, target: str) -> dict[str, Any]:
        tried.append(proxy)
        return {"ok": True, "target": "x", "status": 200, "error": None}

    monkeypatch.setattr(settings_proxy_routes, "try_connection", fake_try)
    manual = {"mode": "manual", "address": "proxy.corp:8080", "username": "alice"}
    elsewhere = {**manual, "address": "elsewhere.example:3128"}
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        client.put("/api/settings/proxy", json={**manual, "password": "s3cret"})
        client.post("/api/settings/proxy/test", json=manual)
        client.post("/api/settings/proxy/test", json=elsewhere)
        moved = client.put("/api/settings/proxy", json=elsewhere).json()

    assert tried == ["http://alice:s3cret@proxy.corp:8080", "http://alice@elsewhere.example:3128"]
    assert moved["password_set"] is False
    assert "s3cret" not in str(dotenv_values(tmp_path / ".env"))


def test_switching_back_to_system_removes_what_manual_wrote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_keyring = _install_fake_keyring(monkeypatch)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("COSCRIBE_DEFAULT_MODEL=fake:model\n", encoding="utf-8")
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        client.put(
            "/api/settings/proxy",
            json={"mode": "manual", "address": "proxy:8080", "username": "a", "password": "b"},
        )
        client.put("/api/settings/proxy", json={"mode": "system"})

    env = dotenv_values(tmp_path / ".env")
    assert env["COSCRIBE_PROXY_MODE"] == "system"
    assert not any(name.upper().endswith("_PROXY") for name in env)
    assert env["COSCRIBE_DEFAULT_MODEL"] == "fake:model"
    assert ("coscribe", "setting:proxy") not in fake_keyring.store


def test_no_proxy_overrides_the_proxy_variables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("HTTPS_PROXY=http://old:3128\n", encoding="utf-8")
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        client.put("/api/settings/proxy", json={"mode": "none"})

    env = dotenv_values(tmp_path / ".env")
    assert env["HTTPS_PROXY"] == env["https_proxy"] == ""
    assert env["NO_PROXY"] == env["no_proxy"] == "*"


def test_a_proxy_address_that_cannot_work_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        response = client.put(
            "/api/settings/proxy", json={"mode": "manual", "address": "socks5://proxy:1080"}
        )

    assert response.status_code == 422
    assert "Only HTTP proxies" in response.json()["error"]
    assert "COSCRIBE_PROXY_MODE" not in dotenv_values(tmp_path / ".env")


def test_test_connection_tries_the_unsaved_setting_against_the_default_models_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("", encoding="utf-8")
    tried: list[tuple[str | None, str]] = []

    def fake_try(proxy: str | None, target: str) -> dict[str, Any]:
        tried.append((proxy, target))
        return {"ok": True, "target": "api.anthropic.com", "status": 404, "error": None}

    monkeypatch.setattr(settings_proxy_routes, "try_connection", fake_try)
    with _client_lg(
        tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[]), default_model="anthropic:x"
    ) as client:
        body = client.post(
            "/api/settings/proxy/test",
            json={"mode": "manual", "address": "proxy:8080", "username": "a", "password": "pw"},
        ).json()
        client.post("/api/settings/proxy/test", json={"mode": "none"})

    assert tried == [
        ("http://a:pw@proxy:8080", "https://api.anthropic.com/"),
        (None, "https://api.anthropic.com/"),
    ]
    assert body["ok"] is True and body["proxy"] == "http://proxy:8080"
    assert "COSCRIBE_PROXY_MODE" not in dotenv_values(tmp_path / ".env")
