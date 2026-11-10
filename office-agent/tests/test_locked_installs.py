"""Every install of office-agent's dependencies goes through uv.lock (scripts/install_locked.py).

A plain `pip install -e ".[dev,web]"` resolves pyproject.toml's ranges afresh, so a workflow
that kept one would test versions nobody locked, and the sidecar would ship them.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
OFFICE_AGENT = ROOT / "office-agent"

# pip installing the project or one of its extras, which would resolve the ranges again.
_UNLOCKED = re.compile(r"pip(?:\.exe)?\s+install\b[^\n]*?(?:\s-e\s|\s\.(?:\[|\s|$)|\"\.\[)")


def _install_locked() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "install_locked", OFFICE_AGENT / "scripts" / "install_locked.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_sources() -> list[Path]:
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    return [*workflows, ROOT / "office-agent-desktop" / "scripts" / "stage-sidecar.sh"]


def test_the_pattern_catches_an_install_of_the_project() -> None:
    assert _UNLOCKED.search('run: pip install -e ".[dev,web]"')
    assert _UNLOCKED.search('pip install ".[dev,web]"')
    assert _UNLOCKED.search(".venv/Scripts/python -m pip install -e .")
    assert not _UNLOCKED.search("pip install mutmut==3.8.1")
    assert not _UNLOCKED.search("pip install keyrings.alt")


@pytest.mark.parametrize("path", _install_sources(), ids=lambda p: p.name)
def test_no_workflow_installs_the_project_from_its_ranges(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert not _UNLOCKED.search(text), (
        f"{path.name} installs office-agent with pip directly; use "
        "`python scripts/install_locked.py --extra ...` so it gets the versions in uv.lock"
    )


def test_the_sidecar_build_installs_from_the_lock_with_pyinstaller() -> None:
    script = (ROOT / "office-agent-desktop/scripts/stage-sidecar.sh").read_text(encoding="utf-8")
    assert "install_locked.py" in script
    assert "--group sidecar" in script


def test_the_export_is_checked_against_pyproject_and_leaves_out_the_project() -> None:
    cmd = _install_locked().export_command(
        "uv", ["dev", "web"], ["sidecar"], Path("requirements.txt")
    )
    # --locked: a range changed without `uv lock` fails instead of installing something else.
    assert "--locked" in cmd
    assert "--no-emit-project" in cmd
    assert cmd[cmd.index("--extra") + 1] == "dev"
    assert cmd[cmd.index("--group") + 1] == "sidecar"


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv on PATH")
def test_the_lock_matches_pyproject() -> None:
    result = subprocess.run(
        ["uv", "lock", "--check", "--offline", "--project", str(OFFICE_AGENT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
