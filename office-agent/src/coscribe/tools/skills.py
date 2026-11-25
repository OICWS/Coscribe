"""Skill loading: SKILL.md discovery and progressive-disclosure tools.

Same convention as Claude Code's own skills (see ARCHITECTURE.md's
"Extension points"): a Skill is a directory with a SKILL.md (YAML frontmatter
name+description, then markdown instructions), plus optional
scripts/references/assets. Metadata (name+description) is always visible to
the Coordinator via its instructions; the full body is loaded on demand via
load_skill, which also gives the skill's absolute folder so its bundled
scripts can be run with run_python_script; other files are read via
read_skill_file.

Two sources, both parsed the same way: `load_skills(settings.skills_dir)`
scans a user/deployment-local directory (gitignored, empty by default --
nothing ships there) for skills a user or org authors themselves;
`load_builtin_skills()` scans `src/coscribe/builtin_skills/`, coscribe's
own bundled skills (pptx/excel/word design guidance), shipped with the
package so a fresh install has real content without the user writing any
SKILL.md themselves. `coordinator.py` combines both.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..runtime import tool_metadata

logger = logging.getLogger(__name__)


def slugify_skill_name(name: str) -> str:
    """Kebab-case a skill's display name into its directory slug -- e.g.
    "Weekly Report Format" -> "weekly-report-format". Same convention the
    Skill Creator meta-skill's own step 5 already documents by hand
    (`builtin_skills/skill-creator/SKILL.md`); this is the mechanical
    version /create-skill (runtime_lg/skill_authoring.py) uses instead of
    asking the curator model to invent one -- a slug has to be
    deterministic and filesystem-safe, not a judgment call."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "skill"


# /create-skill's curator call (runtime_lg/skill_authoring.py's
# propose_skill_save_lg) -- decides what to write into a NEW skill's
# description/body.
SKILL_SAVE_CURATOR_INSTRUCTIONS = """\
You are deciding what to write when the user asks to save the
conversation below as a reusable Skill named "<name>" (a SKILL.md
Coscribe can load again in a future, unrelated conversation). You are
NOT executing anything -- only writing the skill's own description and
body.

You'll see the proposed skill name and the full conversation transcript.
You may also see a previous clarification exchange, if the user already
answered an earlier question from you about this same save.

A Skill is generalized, reusable KNOWLEDGE OR PROCEDURE -- how to do a
kind of task -- not a literal transcript of this one conversation, and
not a fixed sequence of tool calls replayed with the same exact
arguments every time (that's what a scheduled task is for -- don't
write one of those under a different name). Write the
body as direct instructions to a future agent picking this up cold,
generalized from what actually happened here: what the task is, what to
watch out for (a real mistake made and corrected in this conversation is
worth calling out explicitly, since it's exactly the kind of thing worth
not repeating), what good output looks like. Strip out anything specific
to just this one instance (a particular file name, a particular number)
unless it's a genuinely fixed part of the procedure every time, not an
example value.

Decide one of two things:

1. If a clear, generalizable procedure is identifiable in the
transcript, write it:
   - "description": one line stating the trigger condition -- when a
     future agent should load this skill. This is the ONLY thing visible
     before the skill is loaded, so it has to be specific enough to fire
     at the right moment and not otherwise. State it as "load when/before
     X", not a vague summary of the content.
   - "body": the actual instructions, in Markdown -- direct guidance to
     a future agent, not commentary about the skill itself.

2. If you genuinely can't tell what should be captured -- the
conversation covers multiple unrelated tasks with no single clear
procedure, or there isn't enough here yet to generalize from -- ask ONE
short, specific clarifying question instead of guessing. Only do this
when actually unclear; most conversations with a real task in them have
an obvious answer and should not be questioned needlessly.

Respond with ONLY a JSON object, one of exactly these two shapes,
nothing else:
{"decision": "clarify", "question": "..."}
{"decision": "propose", "description": "...", "body": "..."}
"""


@dataclass
class SkillInfo:
    name: str
    description: str
    dir: Path
    body: str
    # Set for a skill that came from a plugin's `skills/` folder (decision 0058); a lone
    # SKILL.md folder is a one-skill plugin of its own and leaves these unset.
    plugin: str | None = None
    plugin_dir: Path | None = None

    def plugin_info(self) -> dict[str, Any] | None:
        """What Settings shows of the plugin this skill came from, None for a lone skill."""
        if self.plugin_dir is None:
            return None
        manifest = plugin_manifest(self.plugin_dir) or {}
        author = manifest.get("author")
        if isinstance(author, dict):
            author = author.get("name")
        return {
            "name": self.plugin,
            "description": str(manifest.get("description") or ""),
            "version": str(manifest.get("version") or ""),
            "author": str(author or ""),
            "tools": self.builtin_tools(),
            "unused": [
                label
                for label, paths in _UNUSED_PARTS
                if any((self.plugin_dir / path).exists() for path in paths)
            ],
        }

    def builtin_tools(self) -> list[str]:
        """The built-in tools this skill's plugin brings (its manifest's `coscribe.tools`). Only
        a plugin shipped with Coscribe brings any: an installed one adds instructions and scripts,
        never a tool of the app (decision 0058)."""
        if self.plugin_dir is None or self.plugin_dir.parent != _BUILTIN_SKILLS_DIR:
            return []
        extension = (plugin_manifest(self.plugin_dir) or {}).get("coscribe")
        tools = extension.get("tools") if isinstance(extension, dict) else None
        return [t for t in tools if isinstance(t, str)] if isinstance(tools, list) else []

    @property
    def slug(self) -> str:
        """The single-token identifier for the /<slug> chat command (see
        conversation/session.py's skills_by_name and web/app.py's /api/commands) --
        the skill's own directory name, lowercased. `name` is a human-
        readable display label that can contain spaces ("Skill Creator",
        "Word Documents"), so it can't be typed as a single command token
        directly; the directory name is already guaranteed unique (one
        skill per directory, per _scan_skills_dir) and already matches
        this convention for every skill the Skill Creator meta-skill
        itself creates (its own step 5: "pick a kebab-case directory slug
        from the skill's name"), so this reuses it rather than deriving a
        second, possibly-colliding slug from `name` independently."""
        return self.dir.name.lower()


def load_skills(skills_dir: str | Path, *, create_if_missing: bool = True) -> list[SkillInfo]:
    """Scan skills_dir's immediate subdirectories for a SKILL.md each.

    A subdirectory without one isn't a skill (silently skipped); a SKILL.md
    that's missing or has malformed frontmatter is a skill someone meant to
    write but got wrong -- logged and skipped, not fatal to startup. A folder's own
    `.coscribe/skills` is only read, never made (`create_if_missing=False`).
    """
    return _scan_skills_dir(Path(skills_dir), create_if_missing=create_if_missing)


_BUILTIN_SKILLS_DIR = Path(__file__).resolve().parent.parent / "builtin_skills"


def load_builtin_skills() -> list[SkillInfo]:
    """Scan coscribe's own bundled skills (src/coscribe/builtin_skills/) --
    shipped with the package itself, distinct from load_skills'
    settings.skills_dir, which is a user/deployment-local, gitignored
    directory (see .gitignore's `/skills/`) that never ships any content.
    Built-in skills need this separate, fixed location so a fresh install
    has real skill content available without the user authoring their own
    SKILL.md files first -- exactly the non-technical-user gap this exists
    to close."""
    return _scan_skills_dir(_BUILTIN_SKILLS_DIR, create_if_missing=False)


def _scan_skills_dir(root: Path, *, create_if_missing: bool) -> list[SkillInfo]:
    if create_if_missing:
        root.mkdir(parents=True, exist_ok=True)
    elif not root.is_dir():
        return []
    skills: list[SkillInfo] = []
    for entry in sorted(root.iterdir()):
        # A dot-folder is a skill still being downloaded (skill_catalog.py).
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        if is_plugin_dir(entry):
            skills += _plugin_skills(entry, {skill.name for skill in skills})
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue
        try:
            skills.append(_parse_skill(entry, skill_md))
        except Exception:
            logger.warning("Skipping skill in %r: failed to parse SKILL.md", entry, exc_info=True)
    return skills


# Where Claude and Codex keep a plugin's manifest (decision 0058); either one, or none, may be
# there. A plugin's skills sit in `skills/` unless its manifest names other folders.
# Parts of a Claude or Codex plugin that Coscribe reads but does not use (decision 0058).
_UNUSED_PARTS = (
    ("commands", ("commands",)),
    ("agents", ("agents",)),
    ("hooks", ("hooks", "hooks.json")),
    ("MCP servers", (".mcp.json", "mcp.json")),
    ("apps", (".app.json",)),
    ("LSP servers", (".lsp.json",)),
)
_MANIFEST_PATHS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json")


def plugin_manifest(plugin_dir: Path) -> dict[str, Any] | None:
    """The plugin's manifest, or None when it has none or it isn't a JSON object."""
    import json

    for relative in _MANIFEST_PATHS:
        path = plugin_dir / relative
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                logger.warning("Ignoring unreadable plugin manifest %r", path)
                return None
            return data if isinstance(data, dict) else None
    return None


def is_plugin_dir(path: Path) -> bool:
    # A folder with its own SKILL.md and nothing else is a one-skill plugin, read as a skill.
    return any((path / relative).is_file() for relative in _MANIFEST_PATHS) or (
        (path / "skills").is_dir() and not (path / "SKILL.md").is_file()
    )


def _plugin_skill_roots(plugin_dir: Path, manifest: dict[str, Any] | None) -> list[Path]:
    declared = (manifest or {}).get("skills")
    if isinstance(declared, str):
        declared = [declared]
    if not isinstance(declared, list) or not declared:
        declared = ["skills"]
    roots = []
    resolved_plugin = plugin_dir.resolve()
    for relative in declared:
        if not isinstance(relative, str):
            continue
        candidate = (plugin_dir / relative).resolve()
        # A manifest is someone else's file: a path out of the plugin is not followed.
        if candidate.is_relative_to(resolved_plugin) and candidate.is_dir():
            roots.append(candidate)
    return roots


def _plugin_skills(plugin_dir: Path, taken: set[str]) -> list[SkillInfo]:
    manifest = plugin_manifest(plugin_dir)
    plugin_name = str((manifest or {}).get("name") or plugin_dir.name)
    skills: list[SkillInfo] = []
    for skills_root in _plugin_skill_roots(plugin_dir, manifest):
        # A root that is itself one skill (`"skills": "./my-skill"`) counts as that skill.
        candidates = (
            [skills_root]
            if (skills_root / "SKILL.md").is_file()
            else sorted(p for p in skills_root.iterdir() if p.is_dir())
        )
        for skill_dir in candidates:
            skill_md = skill_dir / "SKILL.md"
            if skill_dir.name.startswith(".") or not skill_md.is_file():
                continue
            try:
                skill = _parse_skill(skill_dir, skill_md)
            except Exception:
                logger.warning("Skipping skill in %r: failed to parse SKILL.md", skill_dir)
                continue
            if skill.name in taken:
                logger.warning(
                    "Skipping %r in plugin %r: a skill has that name", skill.name, plugin_name
                )
                continue
            skill.plugin, skill.plugin_dir = plugin_name, plugin_dir
            taken.add(skill.name)
            skills.append(skill)
    return skills


def parse_skill_frontmatter(text: str) -> tuple[str, str, str]:
    """Parse a SKILL.md's YAML frontmatter (name, description) and body --
    shared by disk-scanning (_parse_skill) and upload validation
    (save_uploaded_skill) below, so both apply the exact same rules."""
    try:
        _, raw_frontmatter, body = text.split("---", 2)
    except ValueError:
        raise ValueError("SKILL.md must start with a '---' YAML frontmatter block") from None
    frontmatter = yaml.safe_load(raw_frontmatter) or {}
    name, description = frontmatter.get("name"), frontmatter.get("description")
    if not name or not description:
        raise ValueError("SKILL.md frontmatter needs name and description")
    return str(name), str(description), body.strip()


def _parse_skill(skill_dir: Path, skill_md: Path) -> SkillInfo:
    name, description, body = parse_skill_frontmatter(skill_md.read_text(encoding="utf-8"))
    return SkillInfo(name=name, description=description, dir=skill_dir, body=body)


class SkillUploadError(ValueError):
    """Raised by save_uploaded_skill on anything the caller should surface
    to the user as a 400, not a 500 -- bad structure, name collision, a
    zip entry that escapes its own folder."""


def save_uploaded_skill(skills_dir: str | Path, filename: str, content: bytes) -> SkillInfo:
    """Validate and write an uploaded skill into skills_dir/<slug>/ -- the
    real half of Settings > Skills > Add > Upload skill. Two accepted
    shapes, as that page lists them:
    - a bare `.md` file: becomes skills_dir/<slug>/SKILL.md directly.
    - a `.zip`/`.skill` archive: must contain a SKILL.md, either at the
      archive's top level or one directory level down (the shape you get
      zipping a folder named after the skill) -- any sibling
      scripts/references/assets entries are extracted as-is, matching the
      standard skill folder layout this module's own docstring describes;
      no per-file validation beyond the zip-slip guard below.
    No security/malware scanning -- deliberately out of scope, see
    ROADMAP.md's Phase 8am item 4.
    """
    root = Path(skills_dir)
    root.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix.lower()
    if suffix == ".md":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SkillUploadError("SKILL.md must be UTF-8 text") from exc
        try:
            name, _, _ = parse_skill_frontmatter(text)
        except ValueError as exc:
            raise SkillUploadError(str(exc)) from exc
        target = root / slugify_skill_name(name)
        if target.exists():
            raise SkillUploadError(f"A skill named {name!r} already exists")
        target.mkdir(parents=True)
        (target / "SKILL.md").write_bytes(content)
        return _parse_skill(target, target / "SKILL.md")
    if suffix in (".zip", ".skill", ".plugin"):
        return _save_uploaded_skill_archive(root, content)
    raise SkillUploadError(f"Unsupported file type {suffix!r} -- use .md, .zip, .skill or .plugin")


def _save_uploaded_skill_archive(root: Path, content: bytes) -> SkillInfo:
    import io
    import json
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            plugin_prefix = _plugin_prefix(names)
            if plugin_prefix is not None:
                manifest_name = next(
                    (plugin_prefix + m for m in _MANIFEST_PATHS if plugin_prefix + m in names), None
                )
                manifest: Any = {}
                if manifest_name is not None:
                    try:
                        manifest = json.loads(zf.read(manifest_name).decode("utf-8"))
                    except (UnicodeDecodeError, ValueError) as exc:
                        raise SkillUploadError(f"{manifest_name} isn't valid JSON") from exc
                fallback = plugin_prefix.rstrip("/") or "plugin"
                name = (
                    str(manifest.get("name") or fallback)
                    if isinstance(manifest, dict)
                    else fallback
                )
                target = root / slugify_skill_name(name)
                if target.exists():
                    raise SkillUploadError(f"A skill or plugin named {name!r} already exists")
                _extract(zf, plugin_prefix, target)
                skills = _plugin_skills(target, set())
                if not skills:
                    import shutil

                    shutil.rmtree(target, ignore_errors=True)
                    raise SkillUploadError(f"Plugin {name!r} has no skill with a SKILL.md")
                return skills[0]
            # SKILL.md at the top level or exactly one folder down (the
            # shape you get zipping a folder) -- prefer the shallowest
            # match.
            candidates = [n for n in names if Path(n).name == "SKILL.md" and n.count("/") <= 1]
            if not candidates:
                raise SkillUploadError(
                    "Archive must contain a SKILL.md at its top level or one folder down"
                )
            skill_md_name = min(candidates, key=lambda n: n.count("/"))
            prefix = skill_md_name.rsplit("/", 1)[0] + "/" if "/" in skill_md_name else ""

            try:
                text = zf.read(skill_md_name).decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SkillUploadError("SKILL.md must be UTF-8 text") from exc
            try:
                name, _, _ = parse_skill_frontmatter(text)
            except ValueError as exc:
                raise SkillUploadError(str(exc)) from exc
            target = root / slugify_skill_name(name)
            if target.exists():
                raise SkillUploadError(f"A skill named {name!r} already exists")
            _extract(zf, prefix, target)
            return _parse_skill(target, target / "SKILL.md")
    except zipfile.BadZipFile as exc:
        raise SkillUploadError("Not a valid zip archive") from exc


def _plugin_prefix(names: list[str]) -> str | None:
    """The folder of an archive that holds a plugin (a manifest, or a `skills/` folder without
    its own SKILL.md), at the top level or one folder down; None when it holds a lone skill."""
    for prefix in sorted({""} | {n.split("/", 1)[0] + "/" for n in names if "/" in n}, key=len):
        if any(prefix + m in names for m in _MANIFEST_PATHS):
            return prefix
        if prefix + "SKILL.md" not in names and any(
            n.startswith(prefix + "skills/") and n.endswith("/SKILL.md") for n in names
        ):
            return prefix
    return None


def _extract(zf: Any, prefix: str, target: Path) -> None:
    resolved_target = target.resolve()
    for member in zf.namelist():
        if not member.startswith(prefix) or member == prefix:
            continue
        relative = member[len(prefix) :]
        dest = (target / relative).resolve()
        if not dest.is_relative_to(resolved_target):
            import shutil

            shutil.rmtree(target, ignore_errors=True)
            raise SkillUploadError("Archive contains an entry outside its own folder")
        if member.endswith("/"):
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(member))


# A server's name and host come from someone else's file and reach the model: only one short
# word each passes, so the file cannot add sentences of its own to a tool result.
_SERVICE_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}")
_MAX_SERVICES = 8


def _plugin_services(plugin_dir: Path) -> list[str]:
    """The services a plugin's MCP servers reach, by name and host, read from its `.mcp.json`
    or its manifest's `mcpServers`. A hint only: no server in it is added or started (decision
    0058)."""
    import json
    from urllib.parse import urlparse

    servers: Any = (plugin_manifest(plugin_dir) or {}).get("mcpServers")
    if not isinstance(servers, dict):
        servers = None
        for relative in (".mcp.json", "mcp.json"):
            path = plugin_dir / relative
            if path.is_file():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    return []
                if isinstance(data, dict):
                    servers = data.get("mcpServers", data)
                break
    if not isinstance(servers, dict):
        return []
    services: list[str] = []
    for name, config in servers.items():
        if not (isinstance(name, str) and _SERVICE_WORD.fullmatch(name)):
            continue
        url = config.get("url") if isinstance(config, dict) else None
        host = urlparse(url).hostname if isinstance(url, str) else None
        label = f"{name} ({host})" if host and _SERVICE_WORD.fullmatch(host) else name
        if label not in services:
            services.append(label)
    return services[:_MAX_SERVICES]


def _connector_hint(plugin_dir: Path) -> str:
    services = _plugin_services(plugin_dir)
    if not services:
        return ""
    return (
        f"\n(This skill's plugin was written for these services: {', '.join(services)}. "
        "Coscribe does not start a plugin's servers. If the work needs one of them and no tool "
        "you have reaches it (look with search_tools), call find_connector with the service's "
        "name and offer what it finds with offer_connector; never ask the user to set up the "
        "plugin's server.)"
    )


def format_skill_listing(skills: list[SkillInfo]) -> str:
    """Render the always-visible "name: description" block for the system
    instructions -- level 1 of progressive disclosure."""
    lines = ["Available skills (call load_skill(name) before following one):"]
    lines += [f"- {skill.name}: {skill.description}" for skill in skills]
    return "\n".join(lines)


def build_skill_tools(skills: list[SkillInfo]) -> list[Callable[..., Any]]:
    """Return the load_skill/read_skill_file tool callables, bound to the
    given skills -- levels 2 and 3 of progressive disclosure."""
    by_name = {skill.name: skill for skill in skills}

    def load_skill(name: str) -> str:
        """Load a skill's full instructions before following them.

        Args:
            name: skill name, as listed in "Available skills"
        """
        skill = by_name.get(name)
        if skill is None:
            raise ValueError(f"Unknown skill: {name!r}. Available: {sorted(by_name)}")
        # Skills written for other agents refer to their own scripts and
        # assets by relative path; the absolute folder lets a script run
        # through run_python_script find them.
        body = skill.body
        if skill.plugin_dir is not None:
            # Claude's plugins name their own scripts by this variable.
            body = body.replace("${CLAUDE_PLUGIN_ROOT}", str(skill.plugin_dir.resolve()))
        hint = _connector_hint(skill.plugin_dir) if skill.plugin_dir is not None else ""
        return (
            f"(This skill's folder is {skill.dir.resolve()} -- read its files with "
            f"read_skill_file; a bundled script can be run with run_python_script, "
            f"e.g. runpy.run_path on its absolute path.){hint}\n\n{body}"
        )

    def read_skill_file(name: str, path: str) -> str:
        """Read a bundled reference/asset file within a skill's own directory
        (e.g. a REFERENCE.md the skill's instructions point you to).

        Args:
            name: skill name
            path: file path relative to the skill's own directory
        """
        skill = by_name.get(name)
        if skill is None:
            raise ValueError(f"Unknown skill: {name!r}")
        resolved = (skill.dir / path).resolve()
        # A plugin's skill may point to files elsewhere in its plugin (shared scripts).
        allowed = skill.plugin_dir if skill.plugin_dir is not None else skill.dir
        try:
            resolved.relative_to(allowed.resolve())
        except ValueError as exc:
            raise PermissionError(f"Path escapes skill directory: {path}") from exc
        if not resolved.is_file():
            raise ValueError(f"File does not exist in skill {name!r}: {path}")
        return resolved.read_text(encoding="utf-8")

    return [
        tool_metadata(load_skill, risk_category="READ", category="skills"),
        tool_metadata(read_skill_file, risk_category="READ", category="skills"),
    ]
