import io
import zipfile
from pathlib import Path

import pytest

from coscribe.runtime import get_tool_metadata
from coscribe.tools.skills import (
    SkillUploadError,
    build_skill_tools,
    format_skill_listing,
    load_builtin_skills,
    load_skills,
    save_uploaded_skill,
)


def _write_skill(skills_dir: Path, name: str, content: str) -> Path:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


SIMPLE_SKILL = """\
---
name: demo
description: A demo skill for testing.
---

# Demo Skill

Do the demo thing.
"""


def test_missing_dir_returns_empty_and_gets_created(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    assert not skills_dir.exists()

    skills = load_skills(skills_dir)

    assert skills == []
    assert skills_dir.is_dir()


def test_parses_well_formed_skill(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo", SIMPLE_SKILL)

    skills = load_skills(tmp_path)

    assert len(skills) == 1
    skill = skills[0]
    assert skill.name == "demo"
    assert skill.description == "A demo skill for testing."
    assert skill.body == "# Demo Skill\n\nDo the demo thing."
    assert skill.dir == tmp_path / "demo"


def test_subdirectory_without_skill_md_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "not-a-skill").mkdir()
    (tmp_path / "not-a-skill" / "readme.txt").write_text("hi")

    assert load_skills(tmp_path) == []


def test_malformed_skill_is_skipped_but_siblings_still_load(tmp_path: Path) -> None:
    _write_skill(tmp_path, "broken", "---\nname: broken\n---\nno description field")
    _write_skill(tmp_path, "good", SIMPLE_SKILL)

    skills = load_skills(tmp_path)

    assert [s.name for s in skills] == ["demo"]  # from SIMPLE_SKILL's frontmatter


def test_load_skill_returns_body_and_raises_for_unknown(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo", SIMPLE_SKILL)
    skills = load_skills(tmp_path)
    tools = {tool.__name__: tool for tool in build_skill_tools(skills)}  # type: ignore[attr-defined]

    loaded = tools["load_skill"](name="demo")
    assert loaded.endswith("# Demo Skill\n\nDo the demo thing.")
    assert str((tmp_path / "demo").resolve()) in loaded
    with pytest.raises(ValueError, match="Unknown skill"):
        tools["load_skill"](name="nope")


def test_read_skill_file_reads_bundled_reference(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, "demo", SIMPLE_SKILL)
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "notes.md").write_text("extra detail")
    skills = load_skills(tmp_path)
    tools = {tool.__name__: tool for tool in build_skill_tools(skills)}  # type: ignore[attr-defined]

    content = tools["read_skill_file"](name="demo", path="references/notes.md")

    assert content == "extra detail"


def test_read_skill_file_rejects_path_escape(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo", SIMPLE_SKILL)
    (tmp_path / "secret.txt").write_text("nope")
    skills = load_skills(tmp_path)
    tools = {tool.__name__: tool for tool in build_skill_tools(skills)}  # type: ignore[attr-defined]

    with pytest.raises(PermissionError):
        tools["read_skill_file"](name="demo", path="../secret.txt")


def test_read_skill_file_raises_for_unknown_skill_or_missing_file(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo", SIMPLE_SKILL)
    skills = load_skills(tmp_path)
    tools = {tool.__name__: tool for tool in build_skill_tools(skills)}  # type: ignore[attr-defined]

    with pytest.raises(ValueError, match="Unknown skill"):
        tools["read_skill_file"](name="nope", path="notes.md")
    with pytest.raises(ValueError, match="does not exist"):
        tools["read_skill_file"](name="demo", path="notes.md")


def test_skill_tools_are_low_risk_no_approval(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo", SIMPLE_SKILL)
    skills = load_skills(tmp_path)
    tools = {tool.__name__: tool for tool in build_skill_tools(skills)}  # type: ignore[attr-defined]

    for name in ("load_skill", "read_skill_file"):
        metadata = get_tool_metadata(tools[name])
        assert metadata.risk_category == "READ"
        assert metadata.requires_approval is False


def test_format_skill_listing(tmp_path: Path) -> None:
    _write_skill(tmp_path, "demo", SIMPLE_SKILL)
    skills = load_skills(tmp_path)

    listing = format_skill_listing(skills)

    assert "load_skill(name)" in listing
    assert "- demo: A demo skill for testing." in listing


def test_load_builtin_skills_finds_the_four_shipped_skills() -> None:
    # Real content shipped with the package (src/coscribe/builtin_skills/),
    # distinct from load_skills' user-local, gitignored directory -- this
    # is the only test that touches the real bundled files rather than a
    # tmp_path fixture, since load_builtin_skills has no dir parameter to
    # redirect.
    skills = load_builtin_skills()

    names = {s.name for s in skills}
    assert names == {
        "Dashboard",
        "PPTX Slides",
        "PPTX Pages",
        "PPTX Editing",
        "Excel Spreadsheets",
        "Word Documents",
        "Docs",
        "Skill Creator",
        "Design",
        "markdown",
    }
    for skill in skills:
        assert skill.description
        assert skill.body


def test_load_builtin_skills_bodies_reference_the_real_tool_names() -> None:
    by_name = {s.name: s for s in load_builtin_skills()}

    assert "add_pptx_scrim" in by_name["PPTX Slides"].body
    assert "icon-list" in by_name["PPTX Slides"].body
    assert "layout: svg" in by_name["PPTX Slides"].body
    assert "fill_pptx_template" in by_name["PPTX Slides"].body
    assert "write_xlsx_cells" in by_name["Excel Spreadsheets"].body
    assert "modify_xlsx" in by_name["Excel Spreadsheets"].body
    assert "[TOC]" in by_name["Word Documents"].body


# ---------------------------------------------------------------------
# save_uploaded_skill -- Settings > Skills > Add > Upload skill's real
# backend half.
# ---------------------------------------------------------------------


def _zip_bytes(entries: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_upload_md_file_writes_skill_md_under_its_slug(tmp_path: Path) -> None:
    skill = save_uploaded_skill(tmp_path, "whatever.md", SIMPLE_SKILL.encode("utf-8"))

    assert skill.name == "demo"
    assert (tmp_path / "demo" / "SKILL.md").read_text(encoding="utf-8") == SIMPLE_SKILL
    # A fresh load_skills scan finds it too, not just the return value.
    assert [s.name for s in load_skills(tmp_path)] == ["demo"]


def test_upload_md_file_rejects_malformed_frontmatter(tmp_path: Path) -> None:
    with pytest.raises(SkillUploadError, match="name and description"):
        save_uploaded_skill(tmp_path, "bad.md", b"---\nname: bad\n---\nno description")


def test_upload_md_file_name_collision_is_rejected(tmp_path: Path) -> None:
    save_uploaded_skill(tmp_path, "a.md", SIMPLE_SKILL.encode("utf-8"))

    with pytest.raises(SkillUploadError, match="already exists"):
        save_uploaded_skill(tmp_path, "b.md", SIMPLE_SKILL.encode("utf-8"))


def test_upload_zip_with_top_level_skill_md_and_references(tmp_path: Path) -> None:
    archive = _zip_bytes(
        {
            "SKILL.md": SIMPLE_SKILL,
            "references/notes.md": "extra detail",
        }
    )

    skill = save_uploaded_skill(tmp_path, "demo.zip", archive)

    assert skill.name == "demo"
    notes = tmp_path / "demo" / "references" / "notes.md"
    assert notes.read_text(encoding="utf-8") == "extra detail"


def test_upload_zip_with_skill_md_one_folder_down(tmp_path: Path) -> None:
    archive = _zip_bytes(
        {"demo-skill/SKILL.md": SIMPLE_SKILL, "demo-skill/scripts/run.py": "print(1)"}
    )

    skill = save_uploaded_skill(tmp_path, "bundle.skill", archive)

    assert skill.name == "demo"
    assert (tmp_path / "demo" / "scripts" / "run.py").read_text(encoding="utf-8") == "print(1)"


def test_upload_zip_without_skill_md_is_rejected(tmp_path: Path) -> None:
    archive = _zip_bytes({"readme.txt": "hi"})

    with pytest.raises(SkillUploadError, match="must contain a SKILL.md"):
        save_uploaded_skill(tmp_path, "bad.zip", archive)


def test_upload_zip_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = _zip_bytes({"SKILL.md": SIMPLE_SKILL, "../../escape.txt": "nope"})

    with pytest.raises(SkillUploadError, match="outside its own folder"):
        save_uploaded_skill(tmp_path, "evil.zip", archive)


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    with pytest.raises(SkillUploadError, match="Unsupported file type"):
        save_uploaded_skill(tmp_path, "notes.txt", b"whatever")


def test_upload_rejects_bad_zip_bytes(tmp_path: Path) -> None:
    with pytest.raises(SkillUploadError, match="Not a valid zip"):
        save_uploaded_skill(tmp_path, "broken.zip", b"not actually a zip")


def _skill_md(name: str, body: str = "Do it.") -> str:
    return f"---\nname: {name}\ndescription: {name} skill\n---\n{body}\n"


@pytest.mark.parametrize(
    "manifest", [".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json"]
)
def test_a_plugin_folder_loads_each_of_its_skills(tmp_path: Path, manifest: str) -> None:
    plugin = tmp_path / "marketing-folder"
    (plugin / manifest).parent.mkdir(parents=True, exist_ok=True)
    (plugin / manifest).write_text('{"name": "marketing"}', encoding="utf-8")
    _write_skill(plugin / "skills", "brief", _skill_md("brief"))
    _write_skill(plugin / "skills", "seo", _skill_md("seo"))
    _write_skill(tmp_path, "alone", _skill_md("alone"))

    skills = {s.name: s for s in load_skills(tmp_path)}

    assert set(skills) == {"alone", "brief", "seo"}
    assert skills["brief"].plugin == "marketing" and skills["brief"].plugin_dir == plugin
    assert skills["alone"].plugin is None


def test_a_skills_folder_without_a_manifest_is_a_plugin_named_after_its_folder(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path / "kit" / "skills", "one", _skill_md("one"))

    (skill,) = load_skills(tmp_path)

    assert skill.plugin == "kit"


def test_a_manifest_can_name_its_skill_folders_but_not_one_outside_it(tmp_path: Path) -> None:
    plugin = tmp_path / "p"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        '{"name": "p", "skills": ["./extra", "../outside"]}', encoding="utf-8"
    )
    _write_skill(plugin / "extra", "inner", _skill_md("inner"))
    _write_skill(tmp_path / "outside", "stolen", _skill_md("stolen"))

    names = {s.name for s in load_skills(tmp_path) if s.plugin == "p"}

    assert names == {"inner"}


def test_a_plugin_skill_with_a_taken_name_is_skipped(tmp_path: Path) -> None:
    _write_skill(tmp_path, "a-first", _skill_md("same"))
    _write_skill(tmp_path / "b-plugin" / "skills", "same", _skill_md("same"))

    skills = load_skills(tmp_path)

    assert [(s.name, s.plugin) for s in skills] == [("same", None)]


def test_load_skill_fills_in_the_plugin_root_and_read_skill_file_reaches_it(
    tmp_path: Path,
) -> None:
    plugin = tmp_path / "p"
    (plugin / "plugin.json").parent.mkdir(parents=True)
    (plugin / "plugin.json").write_text("{}", encoding="utf-8")
    (plugin / "scripts").mkdir()
    (plugin / "scripts" / "run.py").write_text("print(1)", encoding="utf-8")
    _write_skill(plugin / "skills", "s", _skill_md("s", "Run ${CLAUDE_PLUGIN_ROOT}/scripts/run.py"))
    load_skill, read_skill_file = build_skill_tools(load_skills(tmp_path))

    assert f"Run {plugin.resolve()}/scripts/run.py" in load_skill("s")
    assert read_skill_file("s", "../../scripts/run.py") == "print(1)"
    with pytest.raises(PermissionError):
        read_skill_file("s", "../../../p/../outside.txt")


def test_upload_a_plugin_archive_keeps_the_whole_plugin(tmp_path: Path) -> None:
    archive = _zip_bytes(
        {
            "mkt/.claude-plugin/plugin.json": '{"name": "Marketing Kit"}',
            "mkt/.mcp.json": '{"mcpServers": {}}',
            "mkt/skills/brief/SKILL.md": _skill_md("brief"),
            "mkt/skills/seo/SKILL.md": _skill_md("seo"),
        }
    )

    first = save_uploaded_skill(tmp_path, "mkt.plugin", archive)

    assert first.plugin == "Marketing Kit"
    assert (tmp_path / "marketing-kit" / ".mcp.json").is_file()
    assert {s.name for s in load_skills(tmp_path)} == {"brief", "seo"}


def test_upload_a_plugin_without_skills_is_rejected_and_leaves_nothing(tmp_path: Path) -> None:
    archive = _zip_bytes({"plugin.json": '{"name": "empty"}', "README.md": "hi"})

    with pytest.raises(SkillUploadError, match="no skill"):
        save_uploaded_skill(tmp_path, "empty.zip", archive)
    assert not (tmp_path / "empty").exists()


def test_one_skill_of_a_plugin_is_not_removed_alone_but_the_plugin_is(tmp_path: Path) -> None:
    from coscribe.tools import SkillCatalogError, remove_skill

    skills_dir, state_dir = tmp_path / "skills", tmp_path / "state"
    _write_skill(skills_dir / "kit" / "skills", "one", _skill_md("one"))

    with pytest.raises(SkillCatalogError, match="part of the plugin"):
        remove_skill(skills_dir, state_dir, "one")
    assert remove_skill(skills_dir, state_dir, "kit", plugin=True) == ["one"]
    assert not (skills_dir / "kit").exists()


def test_a_plugin_skill_tells_what_its_plugin_is_and_what_coscribe_leaves_unused(
    tmp_path: Path,
) -> None:
    plugin = tmp_path / "kit"
    (plugin / ".codex-plugin").mkdir(parents=True)
    (plugin / ".codex-plugin" / "plugin.json").write_text(
        '{"name": "kit", "version": "1.2.0", "description": "A kit.", "author": {"name": "Acme"},'
        ' "coscribe": {"tools": ["run_python_script"]}}',
        encoding="utf-8",
    )
    (plugin / "hooks.json").write_text("{}", encoding="utf-8")
    (plugin / ".mcp.json").write_text("{}", encoding="utf-8")
    _write_skill(plugin / "skills", "one", _skill_md("one"))
    _write_skill(tmp_path, "alone", _skill_md("alone"))

    skills = {s.name: s for s in load_skills(tmp_path)}

    assert skills["one"].plugin_info() == {
        "name": "kit",
        "description": "A kit.",
        "version": "1.2.0",
        "author": "Acme",
        "tools": [],
        "unused": ["hooks", "MCP servers"],
    }
    assert skills["alone"].plugin_info() is None


def test_pptx_pages_is_a_built_in_plugin_that_brings_its_build_tool() -> None:
    [skill] = [s for s in load_builtin_skills() if s.name == "PPTX Pages"]

    assert skill.plugin == "pptx-pages"
    assert skill.builtin_tools() == ["build_pptx_from_pages"]
    tools = {t.__name__: t for t in build_skill_tools([skill])}
    assert tools["read_skill_file"](name="PPTX Pages", path="methods/academic-research.md")
