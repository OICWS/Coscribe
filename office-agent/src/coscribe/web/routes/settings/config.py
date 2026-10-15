"""The editable .env settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, get_args

from dotenv import dotenv_values, set_key
from fastapi import (
    APIRouter,
)

from ....config import PermissionMode
from ....runtime import (
    env_resolve_secret_for_display,
    env_value_for_storage,
    harden_file_permissions,
)
from ...provider_catalog import (
    PROVIDER_DEFAULT_MODEL_ENV_VARS,
    PROVIDER_KEY_ENV_VARS,
)
from ...schemas import (
    ConfigUpdate,
)
from ...state import AppState
from ..shared import _mask

# COSCRIBE_-prefixed Settings fields the panel exposes for editing.
# state_dir is deliberately omitted -- internal bookkeeping, not something
# a user needs to reach for.
COSCRIBE_ENV_VARS = [
    "COSCRIBE_DEFAULT_MODEL",
    "COSCRIBE_WORKSPACE_ROOT",
    "COSCRIBE_SKILLS_DIR",
    "COSCRIBE_MEMORY_PATH",
    "COSCRIBE_MCP_CONFIG_PATH",
    "COSCRIBE_PROVIDERS_CONFIG_PATH",
    "COSCRIBE_HOOKS_CONFIG_PATH",
    "COSCRIBE_LOG_LEVEL",
    "COSCRIBE_EXTRA_READABLE_DIRS",
    "COSCRIBE_EXTRA_WRITABLE_DIRS",
    "COSCRIBE_MAX_TURNS",
    "COSCRIBE_DEFAULT_PERMISSION_MODE",
    "COSCRIBE_CODE_MODEL",
    "COSCRIBE_CODE_MODULE_ENABLED",
]


# Settings update_config applies to the running server as well as .env.
LIVE_SETTINGS = {
    "COSCRIBE_DEFAULT_MODEL": "default_model",
    "COSCRIBE_MAX_TURNS": "max_turns",
    "COSCRIBE_DEFAULT_PERMISSION_MODE": "default_permission_mode",
    "COSCRIBE_CODE_MODEL": "code_model",
    "COSCRIBE_CODE_MODULE_ENABLED": "code_module_enabled",
}


# Desktop-shell-consumed, not Settings-backed (see office-agent-desktop's
# sidecar.ts's shouldKeepRunningInBackground(), which reads this same
# .env file directly -- this Python process never branches on it; the
# now-legacy Tauri shell's own src-tauri/src/lib.rs did the equivalent
# before the Electron migration) -- so it's a separate list from
# COSCRIBE_ENV_VARS above for the same reason
# PROVIDER_DEFAULT_MODEL_ENV_VARS already is: update_config's own
# restart_required computation is keyed off COSCRIBE_ENV_VARS membership,
# and this one needs no coscribe-web restart to take effect (the desktop
# shell just re-reads the file at the next window-close, live).
DESKTOP_ENV_VARS = ["COSCRIBE_BACKGROUND_ON_CLOSE", "COSCRIBE_NOTIFICATIONS"]


# Kept in .env rather than the browser's own storage: the desktop app
# serves the page from a new port each launch, and browser storage
# doesn't survive an origin change.
APPEARANCE_ENV_VARS: dict[str, tuple[str, ...]] = {
    "COSCRIBE_THEME": ("system", "light", "dark"),
    "COSCRIBE_INTERFACE_FONT": ("default", "system", "dyslexic"),
    "COSCRIBE_MOTION": ("system", "reduced"),
}


# Blank is a silent footgun for these -- Path("") resolves to Path("."),
# and blank COSCRIBE_DEFAULT_MODEL/COSCRIBE_LOG_LEVEL make Settings()
# construction (default_model) or logging.basicConfig (log_level) raise
# outright on next startup. COSCRIBE_MCP_CONFIG_PATH/HOOKS_CONFIG_PATH
# are deliberately excluded -- config.py's Settings already treats a blank
# string there as "unset" gracefully -- and so are provider API keys, where
# blank just means "not configured," discovered at use time, not startup.
BLANK_UNSAFE_ENV_VARS = {
    "COSCRIBE_DEFAULT_MODEL",
    "COSCRIBE_WORKSPACE_ROOT",
    "COSCRIBE_SKILLS_DIR",
    "COSCRIBE_MEMORY_PATH",
    "COSCRIBE_LOG_LEVEL",
    "COSCRIBE_MAX_TURNS",
    "COSCRIBE_DEFAULT_PERMISSION_MODE",
}


_BOOLEAN_CODE_KEYS = {"COSCRIBE_CODE_MODULE_ENABLED"}


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings

    # -- /api/config, /api/mcp/*, /api/providers/* -- direct ports of
    # web/app.py's identical endpoints (see this module's docstring for the
    # one behavioral difference: config changes here apply to the next new
    # session, not every already-open one).

    @router.get("/api/config")
    async def get_config() -> dict[str, Any]:
        values = dotenv_values(".env")
        result: dict[str, Any] = {}
        for key in PROVIDER_KEY_ENV_VARS:
            value = env_resolve_secret_for_display(values.get(key) or None)
            result[key] = {"set": bool(value), "masked": _mask(value) if value else None}
        for key in PROVIDER_DEFAULT_MODEL_ENV_VARS:
            result[key] = values.get(key) or None
        for key in COSCRIBE_ENV_VARS:
            result[key] = values.get(key) or None
        for key in DESKTOP_ENV_VARS:
            result[key] = values.get(key) or None
        for key in APPEARANCE_ENV_VARS:
            result[key] = values.get(key) or None
        return result

    @router.post("/api/config")
    async def update_config(payload: ConfigUpdate) -> dict[str, Any]:
        allowed = (
            set(PROVIDER_KEY_ENV_VARS)
            | set(PROVIDER_DEFAULT_MODEL_ENV_VARS)
            | set(COSCRIBE_ENV_VARS)
            | set(DESKTOP_ENV_VARS)
            | set(APPEARANCE_ENV_VARS)
        )
        rejected: dict[str, str] = {}
        applied: set[str] = set()
        for key, value in payload.updates.items():
            if key not in allowed:
                continue
            if key in BLANK_UNSAFE_ENV_VARS and not value.strip():
                rejected[key] = "cannot be blank"
                continue
            if key == "COSCRIBE_DEFAULT_MODEL" and ":" not in value:
                rejected[key] = 'must be a "provider:model" string, e.g. "anthropic:sonnet"'
                continue
            if key == "COSCRIBE_CODE_MODEL" and value.strip() and ":" not in value:
                rejected[key] = 'must be a "provider:model" string, or blank for the default model'
                continue
            if key in _BOOLEAN_CODE_KEYS and value not in ("true", "false"):
                rejected[key] = 'must be "true" or "false"'
                continue
            if key == "COSCRIBE_MAX_TURNS" and not (value.strip().isdigit() and int(value) > 0):
                rejected[key] = "must be a positive integer"
                continue
            if key == "COSCRIBE_DEFAULT_PERMISSION_MODE" and value not in get_args(PermissionMode):
                rejected[key] = f"must be one of {', '.join(get_args(PermissionMode))}"
                continue
            if key in APPEARANCE_ENV_VARS and value not in APPEARANCE_ENV_VARS[key]:
                rejected[key] = f"must be one of {', '.join(APPEARANCE_ENV_VARS[key])}"
                continue
            if key in PROVIDER_DEFAULT_MODEL_ENV_VARS and ":" in value:
                rejected[key] = (
                    'must be a bare model id, e.g. "claude-opus-5" -- no "provider:" prefix'
                )
                continue
            if key in PROVIDER_KEY_ENV_VARS:
                set_key(".env", key, env_value_for_storage(f"builtin-provider:{key}", value))
                harden_file_permissions(Path(".env"))
                # Mirror the real value into the process environment too,
                # same reason web/app.py's update_config does -- each
                # provider SDK's own constructor reads straight from
                # os.environ, and a plain .env-file write (possibly now a
                # keyring-ref sentinel) is invisible to this already-running
                # process until a restart. Nothing caches the key:
                # resolve_chat_model (runtime_lg/providers.py) builds a fresh chat
                # model on every call, and so does the context-window lookup.
                os.environ[key] = value
            else:
                set_key(".env", key, value)
                if key in LIVE_SETTINGS:
                    # Read afresh whenever a session starts, so the running
                    # server can take the new value without a restart.
                    live_value: str | int | bool | None = value
                    if key == "COSCRIBE_MAX_TURNS":
                        live_value = int(value)
                    elif key in _BOOLEAN_CODE_KEYS:
                        live_value = value == "true"
                    elif key == "COSCRIBE_CODE_MODEL":
                        live_value = value.strip() or None
                    setattr(settings, LIVE_SETTINGS[key], live_value)
            applied.add(key)
        restart_required = any(
            key in COSCRIBE_ENV_VARS and key not in LIVE_SETTINGS for key in applied
        )
        return {"restart_required": restart_required, "rejected": rejected}

    return router
