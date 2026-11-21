"""What a model can do, from the bundled copy of models.dev and the overrides on top of it.

`catalog.json` is a trimmed copy of https://models.dev/api.json (MIT, models.dev), written
by `scripts/update_model_catalog.py` and refreshed by a scheduled job (decision 0055). The app
never fetches it. `overrides.json` corrects the few rows found wrong, each with a source.
Nothing here guesses: a model the catalog doesn't list has no `ModelInfo`, and the caller falls
back to the conservative default.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_HERE = Path(__file__).parent
CATALOG_PATH = _HERE / "catalog.json"
OVERRIDES_PATH = _HERE / "overrides.json"
SOURCE_URL = "https://models.dev/api.json"

# models.dev leaves `api` empty for providers that have their own SDK; their hosts are these.
_KNOWN_HOSTS = {
    "api.openai.com": "openai",
    "api.anthropic.com": "anthropic",
    "generativelanguage.googleapis.com": "google",
    "api.x.ai": "xai",
    "api.groq.com": "groq",
    "api.mistral.ai": "mistral",
    "api.together.xyz": "togetherai",
    "api.cerebras.ai": "cerebras",
}
# Built-in providers whose coscribe name differs from the models.dev id.
_NAME_ALIASES = {"gemini": "google"}


@dataclass(frozen=True)
class ModelInfo:
    """One model as the catalog describes it; `inputs` holds "image" when it sees images. The
    catalog also keeps a thinking toggle and a deprecated mark, read straight from it until a
    caller needs them here. `source` is "catalog" or "override": an override replaced a field."""

    provider: str
    model: str
    name: str
    inputs: tuple[str, ...]
    reasoning: bool
    effort_levels: tuple[str, ...]
    tools: bool
    context: int | None
    output: int | None
    kind: str
    source: str


def trim(api: dict[str, Any]) -> dict[str, Any]:
    """The catalog file's content from models.dev's whole `api.json`: the fields coscribe reads,
    one entry per model keyed `provider/model`."""
    providers: dict[str, Any] = {}
    models: dict[str, Any] = {}
    for pid, p in sorted(api.items()):
        providers[pid] = {k: p[k] for k in ("name", "api", "npm") if p.get(k)}
        for mid, m in sorted(p.get("models", {}).items()):
            models[f"{pid}/{mid}"] = _trim_model(m)
    return {
        "source": SOURCE_URL,
        "license": "MIT, models.dev",
        "providers": providers,
        "models": models,
    }


def _trim_model(m: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": m.get("name", ""),
        "input": list((m.get("modalities") or {}).get("input") or ["text"]),
        "reasoning": bool(m.get("reasoning")),
        "tools": bool(m.get("tool_call")),
    }
    for option in m.get("reasoning_options") or []:
        if option.get("type") == "effort" and option.get("values"):
            entry["effort"] = list(option["values"])
        elif option.get("type") == "toggle":
            entry["toggle"] = True
    limit = m.get("limit") or {}
    for key in ("context", "output"):
        if limit.get(key):
            entry[key] = int(limit[key])
    if m.get("type") and m["type"] != "chat":
        entry["kind"] = m["type"]
    if m.get("status") == "deprecated":
        entry["deprecated"] = True
    return entry


def dumps(catalog: dict[str, Any]) -> str:
    """The catalog as written to disk: one line per provider and per model, so a refresh's diff
    shows exactly which rows changed."""

    def block(rows: dict[str, Any]) -> str:
        return ",\n".join(
            f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in rows.items()
        )

    head = {k: catalog[k] for k in ("source", "license")}
    return (
        json.dumps(head, ensure_ascii=False)[:-1]
        + ',\n"providers": {\n'
        + block(catalog["providers"])
        + '\n},\n"models": {\n'
        + block(catalog["models"])
        + "\n}}\n"
    )


@cache
def _catalog() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return data


@cache
def _overrides() -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))[
        "models"
    ]
    return data


def catalog_provider(name: str = "", base_url: str = "") -> str | None:
    """The models.dev provider a coscribe provider is: by its base URL's host (the longest
    matching path wins when several share it), or by name when it has no base URL."""
    providers: dict[str, Any] = _catalog()["providers"]
    if not base_url.strip():
        key = _NAME_ALIASES.get(name.lower(), name.lower())
        return key if key in providers else None
    url = urlsplit(base_url.strip())
    host = (url.hostname or "").lower()
    path = url.path.rstrip("/")
    best: tuple[int, str] | None = None
    for pid, p in providers.items():
        api = urlsplit(p.get("api", ""))
        if (api.hostname or "").lower() != host:
            continue
        api_path = api.path.rstrip("/")
        if path.startswith(api_path) and (best is None or len(api_path) > best[0]):
            best = (len(api_path), pid)
    if best is not None:
        return best[1]
    return _KNOWN_HOSTS.get(host)


def model_info(model: str, *, provider: str = "", base_url: str = "") -> ModelInfo | None:
    """What `model` can do on the coscribe provider named `provider` at `base_url`; None when
    the catalog doesn't know that provider or that model."""
    pid = catalog_provider(provider, base_url)
    if pid is None:
        return None
    key = f"{pid}/{model}"
    entry = _catalog()["models"].get(key)
    if entry is None:
        return None
    override = _overrides().get(key, {})
    merged = {**entry, **{k: v for k, v in override.items() if k not in ("source", "checked")}}
    return ModelInfo(
        provider=pid,
        model=model,
        name=merged.get("name", model),
        inputs=tuple(merged.get("input", ("text",))),
        reasoning=bool(merged.get("reasoning")),
        effort_levels=tuple(merged.get("effort", ())),
        tools=bool(merged.get("tools")),
        context=merged.get("context"),
        output=merged.get("output"),
        kind=merged.get("kind", "chat"),
        source="override" if override else "catalog",
    )
