"""Settings › General › Proxy (issue #666): System, Manual or No proxy, saved in `.env` as the proxy
variables every start already loads. The password goes into the keychain through the same helper
as the provider keys (with no keychain, into the owner-only `.env`, as theirs do) and is never
sent back."""

from __future__ import annotations

import asyncio
import sys
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from dotenv import dotenv_values, set_key, unset_key
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ....config import Settings
from ....runtime import (
    DEFAULT_BYPASS,
    PROXY_ENV_VARS,
    PROXY_MODES,
    ProxyError,
    ProxySetting,
    clean_bypass,
    configured_proxy,
    env_delete_secret_if_ref,
    env_resolve_secret_for_display,
    env_value_for_storage,
    harden_file_permissions,
    keychain_available,
    load_custom_providers,
    parse_address,
    proxy_env,
    proxy_url,
    try_connection,
    without_credentials,
)
from ...schemas import ProxyUpdate
from ...state import AppState

MODE_ENV = "COSCRIBE_PROXY_MODE"
ADDRESS_ENV = "COSCRIBE_PROXY_ADDRESS"
BYPASS_ENV = "COSCRIBE_PROXY_BYPASS"
USERNAME_ENV = "COSCRIBE_PROXY_USERNAME"
_KEYCHAIN_REF = "proxy"

# What "Test connection" reaches: the default model's provider, since that is what has to work.
_BUILTIN_TARGETS = {
    "anthropic": "https://api.anthropic.com/",
    "openai": "https://api.openai.com/",
    "gemini": "https://generativelanguage.googleapis.com/",
}
_FALLBACK_TARGET = "https://pypi.org/simple/"


def _env_values() -> dict[str, str | None]:
    return dict(dotenv_values(".env"))


def _saved_mode(values: dict[str, str | None]) -> str:
    mode = values.get(MODE_ENV) or "system"
    return mode if mode in PROXY_MODES else "system"


def _saved_password(values: dict[str, str | None]) -> str:
    try:
        url = env_resolve_secret_for_display(values.get("HTTPS_PROXY") or None) or ""
        password = urlsplit(url).password
    except (RuntimeError, ValueError):
        return ""
    return unquote(password) if password else ""


def _current(values: dict[str, str | None]) -> dict[str, Any]:
    active = configured_proxy()
    return {
        "mode": _saved_mode(values),
        "address": values.get(ADDRESS_ENV) or "",
        "bypass": values.get(BYPASS_ENV) or DEFAULT_BYPASS,
        "username": values.get(USERNAME_ENV) or "",
        "password_set": _saved_mode(values) == "manual" and bool(_saved_password(values)),
        # What this running server uses, which a saved change alters only after a restart.
        "active": without_credentials(active) if active else None,
        "keychain": keychain_available(),
    }


def _setting(payload: ProxyUpdate, values: dict[str, str | None]) -> ProxySetting:
    if payload.mode != "manual":
        return ProxySetting(mode=payload.mode)
    username = payload.username.strip()
    password = payload.password
    if password is None:
        same_user = username == (values.get(USERNAME_ENV) or "")
        password = _saved_password(values) if same_user else ""
    return ProxySetting(
        mode="manual",
        address=parse_address(payload.address),
        bypass=payload.bypass.strip() or DEFAULT_BYPASS,
        username=username,
        password=password if username else "",
    )


def _system_proxy(values: dict[str, str | None]) -> str | None:
    """The proxy System would use. While Manual or No proxy is saved, this process's variables
    are that setting's, so only Windows' own setting is left to read."""
    if _saved_mode(values) == "system":
        return configured_proxy()
    if sys.platform == "win32":
        proxies = urllib.request.getproxies_registry()
        return proxies.get("https") or proxies.get("http") or None
    return None


def _bypassed(setting: ProxySetting, target: str) -> bool:
    host = (urlsplit(target).hostname or "").lower()
    for entry in clean_bypass(setting.bypass).lower().split(","):
        entry = entry.lstrip("*").lstrip(".")
        if entry and (host == entry or host.endswith("." + entry)):
            return True
    return False


def _test_target(settings: Settings) -> str:
    provider = settings.default_model.partition(":")[0]
    if provider in _BUILTIN_TARGETS:
        return _BUILTIN_TARGETS[provider]
    path = settings.providers_config_path
    try:
        custom = load_custom_providers(path) if path is not None else {}
    except (OSError, ValueError, RuntimeError):
        custom = {}
    return custom.get(provider, {}).get("base_url") or _FALLBACK_TARGET


def _write(setting: ProxySetting, values: dict[str, str | None]) -> None:
    # Rewritten below, so the keychain entry of the address saved before goes first.
    env_delete_secret_if_ref(values.get("HTTPS_PROXY"))
    set_key(".env", MODE_ENV, setting.mode)
    if setting.mode == "manual":
        set_key(".env", ADDRESS_ENV, setting.address)
        set_key(".env", BYPASS_ENV, setting.bypass)
        if setting.username:
            set_key(".env", USERNAME_ENV, setting.username)
        elif USERNAME_ENV in values:
            unset_key(".env", USERNAME_ENV)
    url = proxy_url(setting)
    if setting.password:
        url = env_value_for_storage(_KEYCHAIN_REF, url)
    for name, value in proxy_env(setting, url).items():
        set_key(".env", name, value)
    if setting.mode == "system" and _saved_mode(values) != "system":
        # What Manual or No proxy wrote; a proxy written into .env by hand under System stays.
        for name in PROXY_ENV_VARS:
            if name in values:
                unset_key(".env", name)
    harden_file_permissions(Path(".env"))


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings

    async def get_proxy() -> dict[str, Any]:
        return _current(_env_values())

    async def put_proxy(payload: ProxyUpdate) -> Any:
        values = _env_values()
        try:
            setting = _setting(payload, values)
        except ProxyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        _write(setting, values)
        return {**_current(_env_values()), "restart_required": True}

    async def test_proxy(payload: ProxyUpdate) -> Any:
        values = _env_values()
        try:
            setting = _setting(payload, values)
        except ProxyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        target = _test_target(settings)
        proxy: str | None = None
        if setting.mode == "manual" and not _bypassed(setting, target):
            proxy = proxy_url(setting)
        elif setting.mode == "system":
            proxy = _system_proxy(values)
        result = await asyncio.to_thread(try_connection, proxy, target)
        return {**result, "proxy": without_credentials(proxy) if proxy else None}

    router.add_api_route("/api/settings/proxy", get_proxy, methods=["GET"])
    router.add_api_route("/api/settings/proxy", put_proxy, methods=["PUT"])
    router.add_api_route("/api/settings/proxy/test", test_proxy, methods=["POST"])
    return router
