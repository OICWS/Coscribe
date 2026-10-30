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

MAP = {
    "SECURITY.md": {
        "covers": ["office-agent/src/coscribe/tools/exec/", "docs/decisions/"],
        "added_or_removed": [],
    },
    "ARCHITECTURE.md": {
        "covers": [],
        "added_or_removed": ["office-agent/src/coscribe/builtin_skills/"],
    },
}


def _m(*paths: str) -> list[tuple[str, str]]:
    return [("M", path) for path in paths]


def test_a_document_whose_code_changed_must_be_changed_or_named_as_checked() -> None:
    changed = _m("office-agent/src/coscribe/tools/exec/isolation.py", "README.md")

    assert doc_impact.not_looked_at(changed, "", MAP) == {
        "SECURITY.md": ["office-agent/src/coscribe/tools/exec/isolation.py"]
    }
    assert doc_impact.not_looked_at(changed + _m("SECURITY.md"), "", MAP) == {}
    checked = "## What\n...\n- Docs checked: SECURITY.md (the sandbox wording still holds)\n"
    assert doc_impact.not_looked_at(changed, checked, MAP) == {}
    # Naming it elsewhere in the description is not looking at it.
    assert doc_impact.not_looked_at(changed, "Touches: SECURITY.md", MAP)
    assert doc_impact.not_looked_at(_m("office-agent/src/coscribe/web/app.py"), "", MAP) == {}
    readmes = {"README.md": {"covers": ["office-agent/.env.example"], "added_or_removed": []}}
    nested = "Docs checked: office-agent/README.md"
    assert doc_impact.not_looked_at(_m("office-agent/.env.example"), nested, readmes)


def test_an_added_or_removed_path_counts_only_when_a_file_comes_or_goes() -> None:
    skill = "office-agent/src/coscribe/builtin_skills/design/SKILL.md"

    assert doc_impact.not_looked_at(_m(skill), "", MAP) == {}
    assert doc_impact.not_looked_at([("A", skill)], "", MAP) == {"ARCHITECTURE.md": [skill]}


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
        for paths in doc_map.values()
        for cover in paths["covers"] + paths["added_or_removed"]
        if not any(name.startswith(cover) for name in tracked)
    ]
    assert not missing, f"named in docs/doc-map.toml but not in the repository: {missing}"


def test_a_module_card_is_asked_for_when_its_module_gains_loses_or_renames_a_file() -> None:
    cards = [
        "office-agent/src/coscribe/tools/AGENTS.md",
        "office-agent/src/coscribe/tools/exec/AGENTS.md",
    ]
    changes = [
        ("M", "office-agent/src/coscribe/tools/files.py"),
        ("A", "office-agent/src/coscribe/tools/exec/sandbox_two.py"),
        ("M", "office-agent/src/coscribe/tools/__init__.py"),
        ("R100", "office-agent/src/coscribe/tools/old_name.py"),
        ("R100", "office-agent/src/coscribe/tools/new_name.py"),
    ]

    found = doc_impact.cards_affected(changes, cards)

    assert found == {
        "office-agent/src/coscribe/tools/exec/AGENTS.md": [
            "office-agent/src/coscribe/tools/exec/sandbox_two.py"
        ],
        "office-agent/src/coscribe/tools/AGENTS.md": [
            "office-agent/src/coscribe/tools/__init__.py",
            "office-agent/src/coscribe/tools/old_name.py",
            "office-agent/src/coscribe/tools/new_name.py",
        ],
    }
    assert (
        doc_impact.cards_affected([("M", "office-agent/src/coscribe/tools/files.py")], cards) == {}
    )
