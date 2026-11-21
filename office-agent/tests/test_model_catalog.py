"""The bundled model catalog: trimming models.dev, finding a provider, and overrides."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from coscribe.runtime.models import catalog as model_catalog
from coscribe.runtime.models import catalog_provider, model_info

API = {
    "deepseek": {
        "id": "deepseek",
        "name": "DeepSeek",
        "api": "https://api.deepseek.com",
        "npm": "@ai-sdk/openai-compatible",
        "env": ["DEEPSEEK_API_KEY"],
        "models": {
            "deepseek-flash": {
                "name": "DeepSeek Flash",
                "modalities": {"input": ["text", "image"], "output": ["text"]},
                "reasoning": True,
                "reasoning_options": [
                    {"type": "toggle"},
                    {"type": "effort", "values": ["low", "high", "max"]},
                ],
                "tool_call": True,
                "limit": {"context": 1048576, "output": 393216},
                "cost": {"input": 1},
            },
            "deepseek-embed": {"name": "Embed", "type": "embedding", "status": "deprecated"},
        },
    },
    "moonshotai": {"name": "Moonshot", "api": "https://api.moonshot.ai/v1", "models": {}},
    "moonshotai-cn": {"name": "Moonshot CN", "api": "https://api.moonshot.cn/v1", "models": {}},
    "alibaba": {
        "name": "A",
        "api": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": {},
    },
    "alibaba-x": {"name": "B", "api": "https://dashscope.aliyuncs.com/other/v1", "models": {}},
    "openai": {"name": "OpenAI", "models": {}},
    "google": {"name": "Google", "models": {}},
}


@pytest.fixture
def catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(model_catalog.dumps(model_catalog.trim(API)), encoding="utf-8")
    overrides = tmp_path / "overrides.json"
    overrides.write_text(json.dumps({"models": {}}), encoding="utf-8")
    monkeypatch.setattr(model_catalog, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(model_catalog, "OVERRIDES_PATH", overrides)
    model_catalog._catalog.cache_clear()
    model_catalog._overrides.cache_clear()
    yield overrides
    model_catalog._catalog.cache_clear()
    model_catalog._overrides.cache_clear()


def test_trim_keeps_only_what_coscribe_reads_one_line_per_model() -> None:
    text = model_catalog.dumps(model_catalog.trim(API))
    assert json.loads(text)["models"]["deepseek/deepseek-flash"] == {
        "name": "DeepSeek Flash",
        "input": ["text", "image"],
        "reasoning": True,
        "tools": True,
        "toggle": True,
        "effort": ["low", "high", "max"],
        "context": 1048576,
        "output": 393216,
    }
    assert json.loads(text)["models"]["deepseek/deepseek-embed"]["kind"] == "embedding"
    assert any(line.startswith('  "deepseek/deepseek-flash": {') for line in text.splitlines())
    assert "cost" not in text and "DEEPSEEK_API_KEY" not in text


def test_a_provider_is_found_by_host_then_longest_path_then_name(catalog: Path) -> None:
    assert catalog_provider("my-ds", "https://api.deepseek.com/v1") == "deepseek"
    assert catalog_provider("kimi", "https://api.moonshot.cn/v1/") == "moonshotai-cn"
    assert catalog_provider("q", "https://dashscope.aliyuncs.com/compatible-mode/v1") == "alibaba"
    assert catalog_provider("o", "https://api.openai.com/v1") == "openai"
    assert catalog_provider("gemini") == "google"
    assert catalog_provider("deepseek", "https://reseller.example/v1") is None


def test_model_info_reads_the_catalog_and_the_overrides(catalog: Path) -> None:
    info = model_info("deepseek-flash", provider="ds", base_url="https://api.deepseek.com/v1")
    assert info is not None
    assert (info.inputs, info.effort_levels, info.context) == (
        ("text", "image"),
        ("low", "high", "max"),
        1048576,
    )
    assert info.source == "catalog"
    assert model_info("unknown", provider="ds", base_url="https://api.deepseek.com") is None

    catalog.write_text(
        json.dumps(
            {
                "models": {
                    "deepseek/deepseek-flash": {
                        "effort": ["low", "medium"],
                        "source": "https://example.test",
                        "checked": "2026-11-21",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    model_catalog._overrides.cache_clear()
    info = model_info("deepseek-flash", provider="ds", base_url="https://api.deepseek.com")
    assert info is not None and info.effort_levels == ("low", "medium")
    assert info.source == "override"


def test_the_bundled_catalog_and_overrides_load() -> None:
    model_catalog._catalog.cache_clear()
    model_catalog._overrides.cache_clear()
    data = json.loads(model_catalog.CATALOG_PATH.read_text(encoding="utf-8"))
    assert data["source"] == model_catalog.SOURCE_URL and len(data["models"]) > 1000
    for key in json.loads(model_catalog.OVERRIDES_PATH.read_text(encoding="utf-8"))["models"]:
        assert key in data["models"], f"override for a model the catalog lacks: {key}"
