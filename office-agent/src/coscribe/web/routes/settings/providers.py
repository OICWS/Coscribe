"""Model providers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values, set_key
from fastapi import (
    APIRouter,
)

from ....runtime import (
    delete_secret,
    env_delete_secret_if_ref,
    env_value_for_storage,
    harden_file_permissions,
    resolve_secret,
    store_secret,
)
from ....runtime.models import provider_models
from ...provider_catalog import (
    BUILTIN_CATALOG,
    BUILTIN_PROVIDERS,
    PROVIDER_CATALOG,
    builtin_models,
    custom_models,
    model_row,
)
from ...schemas import (
    ProviderModelsRequest,
    ProviderUpdate,
)
from ...state import AppState
from ..shared import _read_providers_raw


def _save_builtin_key(env_key: str, api_key: str) -> bool:
    """Store a built-in provider's new key, or keep the saved one when `api_key` is blank.
    False when it is blank and nothing is saved."""
    if not api_key.strip():
        return bool(os.environ.get(env_key))
    set_key(".env", env_key, env_value_for_storage(f"builtin-provider:{env_key}", api_key))
    harden_file_permissions(Path(".env"))
    # os.environ gets the real value, not whatever .env just got (a keyring ref sentinel
    # there) -- this live process needs the actual key now, not after the next
    # resolve_env_keyring_refs() startup pass.
    os.environ[env_key] = api_key
    return True


def _save_builtin(provider: dict[str, str], api_key: str, models: tuple[list[str], str]) -> bool:
    """`_save_builtin_key`, then the models turned on and the default one."""
    if not _save_builtin_key(provider["api_key_env"], api_key):
        return False
    set_key(".env", provider["models_env"], ",".join(models[0]))
    set_key(".env", provider["default_model_env"], models[1])
    return True


def _custom_key(
    name: str, payload: ProviderUpdate, existing: dict[str, Any] | None
) -> tuple[Any, str] | str:
    """(what providers.json stores, the real key) for a custom provider, keeping the saved
    key when the payload's is blank; a rejection reason when the form can't be saved."""
    api_key = payload.api_key
    if not payload.base_url.strip():
        return "base_url cannot be blank"
    if api_key.strip():
        return store_secret(f"custom-provider:{name}", api_key), api_key
    stored = (existing or {}).get("api_key")
    if not stored:
        return "api_key cannot be blank"
    try:
        return stored, resolve_secret(stored) or ""
    except RuntimeError:
        return "the saved key can't be read here; enter it again"


_OPENAI_BASE_URL = "https://api.openai.com/v1"


def _models_to_save(
    builtin: dict[str, str] | None, payload: ProviderUpdate, existing: dict[str, Any] | None
) -> tuple[list[str], str] | None:
    """(the models turned on, the default one) to save: the payload's, else the ones already
    saved; None when there are none, since the model picker offers nothing else."""
    models = list(dict.fromkeys(m.strip() for m in payload.models if m.strip()))
    default = payload.default_model.strip()
    if not models and not default:
        if builtin is not None:
            models, default = builtin_models(builtin, dotenv_values(".env"))
        else:
            models, default = (
                custom_models(existing or {}),
                (existing or {}).get("default_model", ""),
            )
    if default and default not in models:
        models.insert(0, default)
    if not models:
        return None
    return models, default if default in models else models[0]


def _models_target(
    payload: ProviderModelsRequest, providers_config_path: Path | None
) -> tuple[str, str] | str:
    """(base URL, API key) to list a provider's models with, a blank key falling back to
    the saved one; "catalog" for a built-in that lists nothing OpenAI-compatible; or why it
    can't be listed."""
    name = payload.name.strip()
    api_key = payload.api_key.strip()
    if name.lower() == "openai":
        base_url, api_key = _OPENAI_BASE_URL, api_key or os.environ.get("OPENAI_API_KEY", "")
    elif any(p["key"] == name.lower() for p in BUILTIN_PROVIDERS):
        return "catalog"
    else:
        base_url = payload.base_url.strip()
        if not api_key and providers_config_path is not None:
            stored = _read_providers_raw(providers_config_path)["providers"].get(name, {})
            try:
                api_key = resolve_secret(stored.get("api_key")) or ""
            except RuntimeError:
                api_key = ""
    if not base_url:
        return "Enter the base URL first."
    if not api_key:
        return "Enter the API key first."
    return base_url, api_key


async def list_provider_models(base_url: str, api_key: str) -> dict[str, Any]:
    """The model IDs an OpenAI-compatible service lists at `GET {base_url}/models`, or why
    they couldn't be listed."""
    url = base_url.rstrip("/") + "/models"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
    except httpx.TimeoutException:
        return {"models": [], "error": "The provider didn't answer within 15 s."}
    except httpx.HTTPError as exc:
        return {"models": [], "error": f"Couldn't reach the provider: {exc}."}
    if response.status_code in (401, 403):
        return {"models": [], "error": "The provider refused the API key."}
    if response.status_code >= 400:
        return {"models": [], "error": f"The provider answered {response.status_code} at /models."}
    try:
        data = response.json().get("data")
    except (ValueError, AttributeError):
        data = None
    if not isinstance(data, list):
        return {"models": [], "error": "The provider doesn't list its models at /models."}
    ids = sorted({str(m["id"]) for m in data if isinstance(m, dict) and m.get("id")})
    if not ids:
        return {"models": [], "error": "The provider listed no models."}
    return {"models": ids, "error": None}


async def _provider_models(
    payload: ProviderModelsRequest, providers_config_path: Path | None
) -> dict[str, Any]:
    """Each model the provider lists, as `model_row` describes it."""
    name = payload.name.strip()
    target = _models_target(payload, providers_config_path)
    if target == "catalog":
        rows = [model_row(m.model, name, info=m) for m in provider_models(name)]
        return {"models": rows, "error": None if rows else "The catalog lists no models for it."}
    if isinstance(target, str):
        return {"models": [], "error": target}
    listed = await list_provider_models(*target)
    lookup_url = "" if name.lower() == "openai" else target[0]
    listed["models"] = [model_row(m, name, lookup_url) for m in listed["models"]]
    return listed


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _providers_info = state.providers_info
    context_window_client = state.context_window_client

    @router.get("/api/providers/catalog")
    async def get_providers_catalog() -> list[dict[str, Any]]:
        builtin_entries = [{**entry, "base_url": "", "builtin": True} for entry in BUILTIN_CATALOG]
        custom_entries = [
            {**entry, "default_model": "", "builtin": False} for entry in PROVIDER_CATALOG
        ]
        return [*builtin_entries, *custom_entries]

    @router.get("/api/providers")
    async def get_providers() -> dict[str, Any]:
        return _providers_info()

    async def get_provider_models(payload: ProviderModelsRequest) -> dict[str, Any]:
        """A POST although it changes nothing: the request carries an API key."""
        return await _provider_models(payload, settings.providers_config_path)

    # Registered by call so the dead-code check sees the handler used.
    router.post("/api/providers/models")(get_provider_models)

    @router.post("/api/providers")
    async def add_provider(payload: ProviderUpdate) -> dict[str, Any]:
        name = payload.name.strip()
        if not name:
            return {"restart_required": False, "rejected": {"name": "cannot be blank"}}
        # A blank key on a provider already added keeps the saved one, so changing only its
        # default model or base URL doesn't make the person type the key again.
        blank_key = {"restart_required": False, "rejected": {name: "api_key cannot be blank"}}

        builtin = next((p for p in BUILTIN_PROVIDERS if p["key"] == name.lower()), None)
        path = settings.providers_config_path or Path("./providers.json").resolve()
        raw = _read_providers_raw(path)
        models = _models_to_save(builtin, payload, raw["providers"].get(name))
        if models is None:
            return {"restart_required": False, "rejected": {name: "models cannot be empty"}}

        if builtin is not None:
            if not _save_builtin(builtin, payload.api_key, models):
                return blank_key
            # Nothing caches the key: resolve_chat_model and the context-window lookup
            # both build their client fresh on every call.
            return {"restart_required": False, "rejected": {}}

        keys = _custom_key(name, payload, raw["providers"].get(name))
        if isinstance(keys, str):
            return {"restart_required": False, "rejected": {name: keys}}
        stored_key, api_key = keys

        # Stored on disk via store_secret (keyring ref when available, the
        # real value as a hardened-permission fallback otherwise) --
        # context_window_client.register_custom_provider below gets the
        # real value (api_key), never this.
        entry: dict[str, Any] = {
            "base_url": payload.base_url,
            "api_key": stored_key,
            "models": models[0],
            "default_model": models[1],
        }

        # .resolve() matters here: this path gets persisted both into
        # settings.providers_config_path (kept for the rest of the process's
        # life) and into .env (read back on every future process start) --
        # a bare relative "providers.json" would silently start pointing at
        # a different file the moment the process's cwd ever changes.
        # Confirmed the hard way: a stray real .env in the repo root with a
        # relative COSCRIBE_PROVIDERS_CONFIG_PATH from a previous manual
        # run made a batch of unrelated tests fail with FileNotFoundError,
        # purely because they didn't all chdir the same way.
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
            name, {"base_url": payload.base_url, "api_key": api_key}
        )
        return {"restart_required": False, "rejected": {}}

    @router.delete("/api/providers/{name}")
    async def remove_provider(name: str) -> dict[str, Any]:
        builtin = next((p for p in BUILTIN_PROVIDERS if p["key"] == name.lower()), None)
        if builtin is not None:
            env_delete_secret_if_ref(dotenv_values(".env").get(builtin["api_key_env"]))
            set_key(".env", builtin["api_key_env"], "")
            os.environ.pop(builtin["api_key_env"], None)
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
