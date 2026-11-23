"""Adding a GitHub repository with a marketplace.json as a plugin source."""

import hashlib
import json
from pathlib import Path

import pytest

from coscribe.tools import PluginSources, SkillCatalogError, load_skills
from coscribe.tools.plugin_sources import parse_address

_API = "https://api.github.com/repos/acme/plugins"
_RAW = "https://raw.githubusercontent.com/acme/plugins/c0ffee"


def _blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def fake_github(marketplace_path: str = ".claude-plugin/marketplace.json") -> dict[str, bytes]:
    """The URLs a source is read and installed from, for one repository at commit c0ffee: a
    plugin `notes` inside it, one entry in another repository and one whose name is a path."""
    repo = {
        marketplace_path: json.dumps(
            {
                "name": "acme",
                "owner": {"name": "Acme"},
                "plugins": [
                    {"name": "notes", "source": "./notes"},
                    {"name": "far", "source": {"source": "github", "repo": "acme/far"}},
                    {"name": "../escape", "source": "./notes"},
                ],
            }
        ).encode(),
        "notes/.claude-plugin/plugin.json": json.dumps(
            {"name": "notes", "description": "Tidy notes", "interface": {"displayName": "Notes"}}
        ).encode(),
        "notes/skills/tidy/SKILL.md": b"---\nname: tidy\ndescription: Tidies notes\n---\nTidy.",
    }
    tree = [
        {"path": path, "type": "blob", "sha": _blob(data), "size": len(data)}
        for path, data in repo.items()
    ]
    return {
        f"{_API}/commits/HEAD": json.dumps(
            {"sha": "c0ffee", "commit": {"committer": {"date": "2026-11-20T10:00:00Z"}}}
        ).encode(),
        f"{_API}/git/trees/c0ffee?recursive=1": json.dumps({"tree": tree}).encode(),
        **{f"{_RAW}/{path}": data for path, data in repo.items()},
    }


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("acme/plugins", ("acme/plugins", None)),
        ("https://github.com/acme/plugins.git", ("acme/plugins", None)),
        ("https://github.com/acme/plugins/tree/dev", ("acme/plugins", "dev")),
    ],
)
def test_an_address_names_a_repository_and_maybe_a_branch(
    address: str, expected: tuple[str, str | None]
) -> None:
    assert parse_address(address) == expected


def test_a_codex_marketplace_is_read_and_a_plugin_is_described_by_its_manifest(
    tmp_path: Path,
) -> None:
    files = fake_github(".agents/plugins/marketplace.json")
    source = PluginSources(tmp_path, fetch=files.__getitem__).add("acme/plugins")

    assert source["commit"] == "c0ffee" and source["elsewhere"] == 2
    [plugin] = source["plugins"]
    assert (plugin["title"], plugin["description"], plugin["author"]) == (
        "Notes",
        "Tidy notes",
        "Acme",
    )
    assert plugin["skills"] == ["tidy"]


def test_a_repository_without_a_marketplace_is_refused(tmp_path: Path) -> None:
    files = fake_github("marketplace.json")
    with pytest.raises(SkillCatalogError, match="no marketplace.json"):
        PluginSources(tmp_path, fetch=files.__getitem__).add("acme/plugins")


def test_a_plugin_installs_whole_and_a_changed_file_never_lands(tmp_path: Path) -> None:
    files = fake_github()
    sources = PluginSources(tmp_path, fetch=files.__getitem__)
    sources.add("acme/plugins")
    skills_dir = tmp_path / "skills"
    files[f"{_RAW}/notes/skills/tidy/SKILL.md"] = b"changed"

    with pytest.raises(SkillCatalogError, match="didn't match"):
        sources.install(skills_dir, "gh:acme:plugins:notes")
    assert list(skills_dir.iterdir()) == []

    files[f"{_RAW}/notes/skills/tidy/SKILL.md"] = fake_github()[
        f"{_RAW}/notes/skills/tidy/SKILL.md"
    ]
    assert sources.install(skills_dir, "gh:acme:plugins:notes") == ["tidy"]
    assert [(s.name, s.plugin) for s in load_skills(skills_dir)] == [("tidy", "notes")]
    with pytest.raises(SkillCatalogError, match="already added"):
        sources.install(skills_dir, "gh:acme:plugins:notes")
