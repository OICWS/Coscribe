"""`components.toml` is the component map: it must match the tree, and what is generated from
it (`docs/components.md`, the generated block of `.github/CODEOWNERS`) must not be stale."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "office-agent" / "src" / "coscribe"
LAYERS = {
    "cli",
    "web",
    "conversation",
    "coordinator | runtime_lg",
    "workflows | code_runtime",
    "tools",
    "runtime | config",
    "ui",
}


def _generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gen_components", ROOT / "office-agent" / "scripts" / "gen_components.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gen = _generator()
COMPONENTS = gen.load()


def test_names_are_unique_and_every_entry_is_complete() -> None:
    names = [c["name"] for c in COMPONENTS]
    assert len(names) == len(set(names))
    for item in COMPONENTS:
        assert item["layer"] in LAYERS, item["name"]
        assert item["owner"], item["name"]
        assert (ROOT / item["path"]).exists(), f"{item['name']}: no such path"


def test_a_listed_card_exists_and_every_package_card_is_listed() -> None:
    listed = {c["card"] for c in COMPONENTS if c.get("card")}
    for card in listed:
        assert (ROOT / card).is_file(), card
    on_disk = {p.relative_to(ROOT).as_posix() for p in SRC.glob("*/AGENTS.md")}
    assert on_disk <= listed, f"a card with no component: {sorted(on_disk - listed)}"


def test_every_top_level_package_and_module_is_a_component() -> None:
    paths = {c["path"] for c in COMPONENTS}
    for entry in SRC.iterdir():
        if entry.name in {"__init__.py", "__pycache__"} or not (
            entry.suffix == ".py" or (entry / "__init__.py").exists()
        ):
            continue
        assert entry.relative_to(ROOT).as_posix() in paths, f"not in components.toml: {entry.name}"


def test_generated_files_are_not_stale(capsys: pytest.CaptureFixture[str]) -> None:
    assert gen.main(["--check"]) == 0, capsys.readouterr().out


def test_a_package_with_loose_modules_protects_each_of_them() -> None:
    """`tools` lists its protected modules by hand: a new loose module must not escape the
    contract, and a sub-component or a container of them is entered through its own package."""
    names = {str(c["name"]) for c in COMPONENTS}
    for item in COMPONENTS:
        listed = item.get("protected_modules")
        if not listed:
            continue
        prefix = str(item["path"]).removeprefix("office-agent/src/").replace("/", ".")
        children = {
            entry.stem
            for entry in (ROOT / item["path"]).iterdir()
            if entry.name != "__init__.py"
            and (entry.suffix == ".py" or (entry / "__init__.py").exists())
        }
        owned = {
            child
            for child in children
            if any(name.startswith(f"{item['name']}.{child}") for name in names)
        }
        assert set(listed) == {f"{prefix}.{child}" for child in children - owned}, item["name"]
