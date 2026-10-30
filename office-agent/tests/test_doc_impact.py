from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "doc_impact", ROOT / "office-agent/scripts/doc_impact.py"
)
assert _spec and _spec.loader
doc_impact = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(doc_impact)

MAP = {"SECURITY.md": ["office-agent/src/coscribe/tools/exec/", "docs/decisions/"]}


def test_a_document_whose_code_changed_must_be_changed_or_named_as_checked() -> None:
    changed = ["office-agent/src/coscribe/tools/exec/isolation.py", "README.md"]

    assert doc_impact.not_looked_at(changed, "", MAP) == {
        "SECURITY.md": ["office-agent/src/coscribe/tools/exec/isolation.py"]
    }
    assert doc_impact.not_looked_at(changed + ["SECURITY.md"], "", MAP) == {}
    checked = "## What\n...\n- Docs checked: SECURITY.md (the sandbox wording still holds)\n"
    assert doc_impact.not_looked_at(changed, checked, MAP) == {}
    # Naming it elsewhere in the description is not looking at it.
    assert doc_impact.not_looked_at(changed, "Touches: SECURITY.md", MAP)
    assert doc_impact.not_looked_at(["office-agent/src/coscribe/web/app.py"], "", MAP) == {}
    readmes = {"README.md": ["office-agent/.env.example"]}
    nested = "Docs checked: office-agent/README.md"
    assert doc_impact.not_looked_at(["office-agent/.env.example"], nested, readmes)


def test_every_document_and_path_of_the_map_exists() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    doc_map = doc_impact.load_map()
    assert doc_map
    missing = [doc for doc in doc_map if doc not in tracked]
    missing += [
        cover
        for covers in doc_map.values()
        for cover in covers
        if not any(name.startswith(cover) for name in tracked)
    ]
    assert not missing, f"named in docs/doc-map.toml but not in the repository: {missing}"
