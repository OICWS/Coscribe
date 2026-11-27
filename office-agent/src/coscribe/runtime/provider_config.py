"""Loads user-added OpenAI-compatible LLM provider configs (DeepSeek, Kimi,
GLM, or any other) from a JSON file, parallel to tools/mcp.py's
load_mcp_server_configs."""

from __future__ import annotations

import json
from pathlib import Path

from .secrets import resolve_secret


def load_custom_providers(config_path: Path) -> dict[str, dict[str, str]]:
    """Parse a {"providers": {name: {base_url, api_key, ...}}} JSON file into
    a map of runtime connection settings. The model list and default model
    belong to the UI. `api_key` is resolved via
    runtime/secrets.py's resolve_secret before being returned, so every
    caller here keeps getting a plain string regardless of whether it's
    stored on disk as a keyring reference or (legacy, or keyring
    unavailable) plaintext.

    A configured-but-not-yet-created path (COSCRIBE_PROVIDERS_CONFIG_PATH
    set, but no provider ever added through the Settings > Providers tab,
    which is what actually creates the file -- see web/app.py's
    add_provider) is treated the same as "unset": no custom providers,
    not a startup crash. Every caller here already special-cases `path is
    None` the same way; this just extends that to the equally normal
    "not created yet" case instead of requiring every caller to also
    check `.is_file()`."""
    if not config_path.is_file():
        return {}
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    providers = raw.get("providers")
    if not isinstance(providers, dict):
        raise ValueError(f'{config_path}: expected a top-level "providers" object')
    result: dict[str, dict[str, str]] = {}
    for name, entry in providers.items():
        if not isinstance(entry, dict):
            raise ValueError(f"{config_path}: provider {name!r} must be an object")
        base_url = entry.get("base_url", "")
        api_key = resolve_secret(entry.get("api_key")) or ""
        if not base_url or not api_key:
            raise ValueError(f'{config_path}: provider {name!r} needs "base_url" and "api_key"')
        config = {"base_url": base_url, "api_key": api_key}
        for field in ("api_format", "api_version"):
            if isinstance(value := entry.get(field), str):
                config[field] = value
        result[name] = config
    return result
