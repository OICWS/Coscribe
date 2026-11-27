"""Model providers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

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
    ProviderTestRequest,
    ProviderTestResult,
    ProviderUpdate,
)
from ...state import AppState
from ..shared import _read_providers_raw
from .provider_checks import check_provider_connection


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


# Each built-in's own model list. Anthropic's is not OpenAI-compatible; Gemini serves one through
# its OpenAI compatibility layer.
_BUILTIN_MODEL_LISTS = {
    "openai": "https://api.openai.com/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models?limit=1000",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/models",
}


def _builtin_provider(name: str) -> dict[str, str] | None:
    return next((p for p in BUILTIN_PROVIDERS if p["key"] == name.lower()), None)


def _list_headers(provider: str, api_key: str) -> dict[str, str]:
    if provider == "anthropic":
        return {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    return {"Authorization": f"Bearer {api_key}"}


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


def _connection_problem(base_url: str, api_format: str, api_version: str) -> str | None:
    try:
        url = urlsplit(base_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username is not None:
            return "Enter an HTTP or HTTPS base URL."
        port = url.port
        if port == 0 or url.query or url.fragment:
            return "Enter a base URL without query parameters or a fragment."
    except ValueError:
        return "Enter a valid provider base URL."
    path = url.path.rstrip("/")
    if api_format == "azure":
        if not api_version:
            return "Enter the Azure API version."
        if "/openai" in path:
            return "Enter the Azure resource endpoint, without the /openai deployment path."
    elif path.endswith(("/chat/completions", "/responses")):
        return "Enter the base URL without the final /chat/completions or /responses path."
    return None


def _protocol_to_save(payload: ProviderUpdate, existing: dict[str, Any]) -> dict[str, str] | str:
    api_format = payload.api_format or existing.get("api_format")
    if api_format is None:
        return {}
    api_version = (
        payload.api_version if payload.api_version is not None else existing.get("api_version", "")
    )
    api_version = api_version.strip()
    if problem := _connection_problem(payload.base_url.strip(), api_format, api_version):
        return problem
    options = {"api_format": api_format}
    if api_format == "azure":
        options["api_version"] = api_version
    return options


def _saved_key(entry: dict[str, Any]) -> str:
    try:
        return resolve_secret(entry.get("api_key")) or ""
    except RuntimeError:
        return ""


async def _test_provider(
    payload: ProviderTestRequest, providers_config_path: Path | None
) -> ProviderTestResult:
    name = payload.name.strip()
    if _builtin_provider(name) is not None:
        return ProviderTestResult(error="Select a custom provider to run this test.")
    base_url = payload.base_url.strip()
    api_version = payload.api_version.strip()
    if problem := _connection_problem(
        base_url, payload.api_format or "chat_completions", api_version
    ):
        return ProviderTestResult(error=problem)
    model = payload.model.strip()
    if not model:
        return ProviderTestResult(error="Select a model to test.")
    api_key = payload.api_key.strip()
    if not api_key and providers_config_path is not None:
        saved = _read_providers_raw(providers_config_path)["providers"].get(name, {})
        if saved.get("base_url", "").strip().rstrip("/") == base_url.rstrip("/"):
            api_key = _saved_key(saved)
    if not api_key:
        return ProviderTestResult(error="Enter the API key for this URL.")
    config = {
        "base_url": base_url,
        "api_key": api_key,
        "api_version": api_version,
    }
    if payload.api_format is not None:
        config["api_format"] = payload.api_format
    return ProviderTestResult(
        error=await check_provider_connection(config, model, payload.tool_calling)
    )


def _models_target(
    payload: ProviderModelsRequest, providers_config_path: Path | None
) -> tuple[str, dict[str, str]] | str:
    """(the URL listing a provider's models, the headers it needs), a blank key falling back to
    the saved one; or why it can't be listed."""
    name = payload.name.strip()
    api_key = payload.api_key.strip()
    builtin = _builtin_provider(name)
    if builtin is not None:
        url = _BUILTIN_MODEL_LISTS[builtin["key"]]
        api_key = api_key or os.environ.get(builtin["api_key_env"], "")
    else:
        if payload.api_format == "azure":
            return "Add the Azure deployment name manually."
        base_url = payload.base_url.strip()
        if not base_url:
            return "Enter the base URL first."
        url = base_url.rstrip("/") + "/models"
        if not api_key and providers_config_path is not None:
            stored = _read_providers_raw(providers_config_path)["providers"].get(name, {})
            api_key = _saved_key(stored)
    if not api_key:
        return "Enter the API key first."
    return url, _list_headers(name.lower(), api_key)


async def list_provider_models(url: str, headers: dict[str, str]) -> dict[str, Any]:
    """The model IDs a provider lists at `url` (`{"data": [{"id": ...}]}`, as OpenAI-compatible
    services and Anthropic answer), or why they couldn't be listed."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
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
    # Gemini's compatibility layer may name a model "models/<id>"; chat requests take the bare ID.
    ids = sorted(
        {str(m["id"]).removeprefix("models/") for m in data if isinstance(m, dict) and m.get("id")}
    )
    if not ids:
        return {"models": [], "error": "The provider listed no models."}
    return {"models": ids, "error": None}


async def _provider_models(
    payload: ProviderModelsRequest, providers_config_path: Path | None
) -> dict[str, Any]:
    """Each model the provider lists for this key, as `model_row` describes it."""
    name = payload.name.strip()
    target = _models_target(payload, providers_config_path)
    if isinstance(target, str):
        return {"models": [], "error": target}
    listed = await list_provider_models(*target)
    builtin = _builtin_provider(name) is not None
    lookup_url = "" if builtin else payload.base_url.strip()
    listed["models"] = [model_row(m, name, lookup_url) for m in listed["models"]]
    return listed


def _save_custom_provider(
    state: AppState,
    path: Path,
    raw: dict[str, Any],
    name: str,
    payload: ProviderUpdate,
    models: tuple[list[str], str],
) -> str | None:
    existing = raw["providers"].get(name) or {}
    options = _protocol_to_save(payload, existing)
    if isinstance(options, str):
        return options
    keys = _custom_key(name, payload, existing)
    if isinstance(keys, str):
        return keys
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
        **options,
    }

    raw["providers"][name] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    harden_file_permissions(path)
    if state.settings.providers_config_path is None:
        state.settings.providers_config_path = path
        set_key(".env", "COSCRIBE_PROVIDERS_CONFIG_PATH", str(path))
    # Only context_window_client needs live registration -- the next
    # new session's own model resolves this provider by re-reading
    # providers.json fresh (see _get_session above), not through this
    # client at all.
    state.context_window_client.register_custom_provider(
        name, {"base_url": payload.base_url, "api_key": api_key}
    )
    return None


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

    async def run_provider_test(payload: ProviderTestRequest) -> ProviderTestResult:
        return await _test_provider(payload, settings.providers_config_path)

    router.post("/api/providers/test")(run_provider_test)

    @router.post("/api/providers")
    async def add_provider(payload: ProviderUpdate) -> dict[str, Any]:
        name = payload.name.strip()
        if not name:
            return {"restart_required": False, "rejected": {"name": "cannot be blank"}}
        # A blank key on a provider already added keeps the saved one, so changing only its
        # default model or base URL doesn't make the person type the key again.
        blank_key = {"restart_required": False, "rejected": {name: "api_key cannot be blank"}}

        builtin = _builtin_provider(name)
        # Persist an absolute path so a later working directory cannot change the config file.
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

        problem = _save_custom_provider(state, path, raw, name, payload, models)
        return {"restart_required": False, "rejected": {name: problem} if problem else {}}

    @router.delete("/api/providers/{name}")
    async def remove_provider(name: str) -> dict[str, Any]:
        builtin = _builtin_provider(name)
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
