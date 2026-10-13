"""Model providers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, set_key
from fastapi import (
    APIRouter,
)

from ....runtime import (
    delete_secret,
    env_delete_secret_if_ref,
    env_value_for_storage,
    harden_file_permissions,
    store_secret,
)
from ...provider_catalog import (
    BUILTIN_PROVIDERS,
    PROVIDER_CATALOG,
)
from ...schemas import (
    ProviderUpdate,
)
from ...state import AppState
from ..shared import _read_providers_raw


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _providers_info = state.providers_info
    context_window_client = state.context_window_client

    @router.get("/api/providers/catalog")
    async def get_providers_catalog() -> list[dict[str, Any]]:
        builtin_entries: list[dict[str, Any]] = [
            {
                "name": "anthropic",
                "description": "Anthropic's Claude models.",
                "base_url": "",
                # Unlike the third-party PROVIDER_CATALOG below, this one
                # is worth pinning to a real model ID -- Anthropic doesn't
                # publish a rolling "-latest" alias the way gemini's own
                # "gemini-flash-latest" entry below does, so an empty
                # default would leave the single most common Add-provider
                # path with the worst experience of any entry here.
                # Still real drift, caught live: this was "claude-opus-4-6"
                # until an unrelated bug report exposed it as already
                # stale (no such model -- the current family is Opus 5/
                # Sonnet 5/Haiku 4.5). Whoever bumps coscribe's own
                # supported-model docs should bump this alongside them.
                "default_model": "claude-opus-5",
                "builtin": True,
            },
            {
                "name": "openai",
                "description": "OpenAI's GPT models.",
                "base_url": "",
                "default_model": "",
                "builtin": True,
            },
            {
                "name": "gemini",
                "description": "Google's Gemini models.",
                "base_url": "",
                "default_model": "gemini-flash-latest",
                "builtin": True,
            },
        ]
        custom_entries = [{**entry, "builtin": False} for entry in PROVIDER_CATALOG]
        return [*builtin_entries, *custom_entries]

    @router.get("/api/providers")
    async def get_providers() -> dict[str, Any]:
        return _providers_info()

    @router.post("/api/providers")
    async def add_provider(payload: ProviderUpdate) -> dict[str, Any]:
        name = payload.name.strip()
        if not name:
            return {"restart_required": False, "rejected": {"name": "cannot be blank"}}
        if not payload.api_key.strip():
            return {"restart_required": False, "rejected": {name: "api_key cannot be blank"}}

        builtin = next((p for p in BUILTIN_PROVIDERS if p["key"] == name.lower()), None)
        if builtin is not None:
            env_key = builtin["api_key_env"]
            set_key(
                ".env",
                env_key,
                env_value_for_storage(f"builtin-provider:{env_key}", payload.api_key),
            )
            harden_file_permissions(Path(".env"))
            # os.environ gets the real value, not whatever .env just got
            # (a keyring ref sentinel there) -- this live process needs the
            # actual key now, not after the next resolve_env_keyring_refs()
            # startup pass.
            os.environ[builtin["api_key_env"]] = payload.api_key
            if payload.default_model:
                set_key(".env", builtin["default_model_env"], payload.default_model)
            # No context_window_client.invalidate_provider(...) equivalent
            # needed for the *chat* model -- resolve_chat_model builds fresh
            # every call (see update_config's identical comment above).
            # context_window_client itself is the old-runtime LLMClient
            # class, though, so it keeps that class's real caching behavior
            # and does need this.
            context_window_client.invalidate_provider(builtin["key"])
            return {"restart_required": False, "rejected": {}}

        if not payload.base_url.strip():
            return {"restart_required": False, "rejected": {name: "base_url cannot be blank"}}

        # Stored on disk via store_secret (keyring ref when available, the
        # real value as a hardened-permission fallback otherwise) --
        # context_window_client.register_custom_provider below keeps using
        # payload.api_key directly (the real value), never this.
        entry: dict[str, Any] = {
            "base_url": payload.base_url,
            "api_key": store_secret(f"custom-provider:{name}", payload.api_key),
        }
        if payload.default_model:
            entry["default_model"] = payload.default_model

        # .resolve() matters here: this path gets persisted both into
        # settings.providers_config_path (kept for the rest of the process's
        # life) and into .env (read back on every future process start) --
        # a bare relative "providers.json" would silently start pointing at
        # a different file the moment the process's cwd ever changes.
        # Confirmed the hard way: a stray real .env in the repo root with a
        # relative COSCRIBE_PROVIDERS_CONFIG_PATH from a previous manual
        # run made a batch of unrelated tests fail with FileNotFoundError,
        # purely because they didn't all chdir the same way.
        path = settings.providers_config_path or Path("./providers.json").resolve()
        raw = _read_providers_raw(path)
        raw["providers"][name] = entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        harden_file_permissions(path)
        if settings.providers_config_path is None:
            settings.providers_config_path = path
            set_key(".env", "COSCRIBE_PROVIDERS_CONFIG_PATH", str(path))
        # Only context_window_client needs live registration -- the next
        # new session's own model resolves this provider by re-reading
        # providers.json fresh (see _get_session above), not through this
        # client at all.
        context_window_client.register_custom_provider(
            name, {"base_url": payload.base_url, "api_key": payload.api_key}
        )
        return {"restart_required": False, "rejected": {}}

    @router.delete("/api/providers/{name}")
    async def remove_provider(name: str) -> dict[str, Any]:
        builtin = next((p for p in BUILTIN_PROVIDERS if p["key"] == name.lower()), None)
        if builtin is not None:
            env_delete_secret_if_ref(dotenv_values(".env").get(builtin["api_key_env"]))
            set_key(".env", builtin["api_key_env"], "")
            os.environ.pop(builtin["api_key_env"], None)
            context_window_client.invalidate_provider(builtin["key"])
            return {"restart_required": False}
        if settings.providers_config_path is None or not settings.providers_config_path.is_file():
            return {"restart_required": False}
        raw = _read_providers_raw(settings.providers_config_path)
        removed = raw["providers"].pop(name, None)
        if removed is not None:
            delete_secret(removed.get("api_key"))
        settings.providers_config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        harden_file_permissions(settings.providers_config_path)
        context_window_client.deregister_custom_provider(name)
        return {"restart_required": False}

    return router
