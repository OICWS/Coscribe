"""Plugin sources the person adds to Discover: a GitHub repository with a `marketplace.json`
in the Claude form (in `.claude-plugin/`) or the Codex form (in `.agents/plugins/`),
decision 0058.

Adding a source pins it to the commit its branch points at then and records each listed
plugin's files with their git blob hashes; a file is downloaded at that commit and must match
its hash before anything lands, so what is added is what was listed. No one has reviewed an
added source, unlike Discover's own catalog (`skill_catalog.py`); the page says so. Only
plugins inside the repository are listed: an entry that points to another repository or
package is counted, not followed.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import shutil
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .skill_catalog import SOURCE_MARKER, SkillCatalogError, _download
from .skills import load_skills

_STATE_FILE = "plugin_sources.json"
_API = "https://api.github.com/repos/{repo}"
_RAW = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
_MARKETPLACES = (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json")
_MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json")
_ADDRESS = re.compile(
    r"^(?:(?:https?://)?(?:www\.)?github\.com/)?([A-Za-z0-9-]+)/([A-Za-z0-9._-]+?)(?:\.git)?"
    r"(?:/tree/([^?#]+))?/?$"
)
_PLUGIN_MAX_BYTES = 50_000_000
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


def parse_address(address: str) -> tuple[str, str | None]:
    """`owner/repo`, or a github.com address, optionally `/tree/<branch>`."""
    match = _ADDRESS.match(address.strip())
    if match is None:
        raise SkillCatalogError(
            "Give a GitHub repository as owner/name or https://github.com/owner/name"
        )
    owner, name, ref = match.groups()
    return f"{owner}/{name}", ref


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def _local_path(entry: dict[str, Any], plugin_root: str) -> str | None:
    """Where in the repository a marketplace entry's plugin is, or None when it lives
    elsewhere. Claude writes a relative path string; Codex `{"source": "local", "path"}`."""
    source = entry.get("source")
    if isinstance(source, dict) and source.get("source") == "local":
        source = source.get("path")
    if not isinstance(source, str):
        return None
    if not source.startswith("./") and plugin_root:
        source = f"{plugin_root}/{source}"
    path = posixpath.normpath(source.removeprefix("./"))
    if path.startswith(("..", "/")):
        return None
    return "" if path == "." else path


def _author(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("name")
    return value if isinstance(value, str) else ""


def _skill_names(files: list[dict[str, Any]], plugin_name: str) -> list[str]:
    names = []
    for file in files:
        parts = file["path"].split("/")
        if parts[-1] == "SKILL.md":
            names.append(parts[-2] if len(parts) > 1 else plugin_name)
    return sorted(set(names))


class PluginSources:
    """The sources kept in `<state_dir>/plugin_sources.json`, each with the plugins it listed
    when it was added. `fetch` downloads a URL's bytes (replaced in tests)."""

    def __init__(self, state_dir: Path, *, fetch: Callable[[str], bytes] | None = None) -> None:
        self._path = Path(state_dir) / _STATE_FILE
        self._fetch = fetch or _download

    def sources(self) -> list[dict[str, Any]]:
        try:
            sources: list[dict[str, Any]] = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return sources

    def _save(self, sources: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(sources, indent=1), encoding="utf-8")

    def _get(self, url: str) -> bytes:
        try:
            return self._fetch(url)
        except (httpx.HTTPError, OSError, LookupError) as exc:
            raise SkillCatalogError(f"Couldn't download {url}: {exc}") from exc

    def add(self, address: str) -> dict[str, Any]:
        """Reads the repository's marketplace at its branch's current commit; adding a source
        again re-reads it at the newest commit."""
        repo, ref = parse_address(address)
        try:
            source = self._read(repo, ref)
        except SkillCatalogError:
            raise
        except (ValueError, LookupError, TypeError, AttributeError) as exc:
            # An answer not in the shape GitHub's API or the marketplace format promise.
            raise SkillCatalogError(f"Couldn't read {repo} as a plugin source") from exc
        self._save([s for s in self.sources() if s["repo"] != repo] + [source])
        return source

    def _read(self, repo: str, ref: str | None) -> dict[str, Any]:
        api = _API.format(repo=repo)
        commit_info = json.loads(self._get(f"{api}/commits/{quote(ref or 'HEAD', safe='')}"))
        commit = commit_info["sha"]
        tree = json.loads(self._get(f"{api}/git/trees/{commit}?recursive=1"))
        if tree.get("truncated"):
            raise SkillCatalogError(f"{repo} is too large to read as a plugin source")
        blobs = {e["path"]: e for e in tree["tree"] if e.get("type") == "blob"}
        found = next((path for path in _MARKETPLACES if path in blobs), None)
        if found is None:
            raise SkillCatalogError(
                f"{repo} has no marketplace.json ({' or '.join(_MARKETPLACES)})"
            )
        marketplace = json.loads(self._raw(repo, commit, found))
        metadata = marketplace.get("metadata") or {}
        plugin_root = str(metadata.get("pluginRoot") or "").removeprefix("./").strip("/")
        owner = _author(marketplace.get("owner"))
        plugins, elsewhere = [], 0
        for entry in marketplace.get("plugins") or []:
            path = _local_path(entry, plugin_root) if isinstance(entry, dict) else None
            # The name becomes a folder of the skills directory, so it is never a path.
            if path is None or not _NAME.fullmatch(str(entry.get("name"))):
                elsewhere += 1
                continue
            prefix = f"{path}/" if path else ""
            files = [
                {"path": p[len(prefix) :], "sha": b["sha"], "size": b.get("size", 0)}
                for p, b in blobs.items()
                if p.startswith(prefix) and not p.startswith(".git/")
            ]
            plugins.append(
                {
                    "name": entry["name"],
                    "title": entry.get("displayName") or entry["name"],
                    "description": entry.get("description") or "",
                    "version": entry.get("version") or "",
                    "author": _author(entry.get("author")) or owner,
                    "path": path,
                    "skills": _skill_names(files, entry["name"]),
                    "files": files,
                }
            )
        self._describe(repo, commit, [p for p in plugins if not p["description"]])
        source = {
            "repo": repo,
            "ref": ref,
            "commit": commit,
            "updated": (commit_info.get("commit") or {}).get("committer", {}).get("date", ""),
            "name": marketplace.get("name") or repo,
            "plugins": [p for p in plugins if p["skills"]],
            "elsewhere": elsewhere,
        }
        return source

    def _raw(self, repo: str, commit: str, path: str) -> bytes:
        return self._get(_RAW.format(repo=repo, commit=commit, path=quote(path)))

    def _describe(self, repo: str, commit: str, plugins: list[dict[str, Any]]) -> None:
        """Codex's marketplace names a plugin without describing it; its manifest does."""

        def read(plugin: dict[str, Any]) -> None:
            listed = {f["path"] for f in plugin["files"]}
            manifest_path = next((m for m in _MANIFESTS if m in listed), None)
            if manifest_path is None:
                return
            prefix = f"{plugin['path']}/" if plugin["path"] else ""
            try:
                manifest = json.loads(self._raw(repo, commit, prefix + manifest_path))
            except (SkillCatalogError, ValueError):
                return
            interface = manifest.get("interface") or {}
            plugin["description"] = (
                manifest.get("description") or interface.get("shortDescription") or ""
            )
            plugin["title"] = interface.get("displayName") or plugin["title"]
            plugin["version"] = plugin["version"] or manifest.get("version") or ""
            plugin["author"] = _author(manifest.get("author")) or plugin["author"]

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(read, plugins))

    def remove(self, repo: str) -> None:
        sources = self.sources()
        kept = [s for s in sources if s["repo"] != repo]
        if len(kept) == len(sources):
            raise SkillCatalogError(f"{repo!r} isn't a source")
        self._save(kept)

    def plugin(self, plugin_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """A source's plugin by its id, `gh:<owner>:<repo>:<name>`."""
        parts = plugin_id.split(":", 3)
        if len(parts) == 4 and parts[0] == "gh":
            repo = f"{parts[1]}/{parts[2]}"
            for source in self.sources():
                if source["repo"] == repo:
                    found = next((p for p in source["plugins"] if p["name"] == parts[3]), None)
                    if found is not None:
                        return source, found
        raise SkillCatalogError(f"{plugin_id!r} isn't in Discover")

    def file(self, plugin_id: str, path: str) -> bytes:
        source, plugin = self.plugin(plugin_id)
        entry = next((f for f in plugin["files"] if f["path"] == path), None)
        if entry is None:
            raise SkillCatalogError(f"No such file: {path!r}")
        return self._checked(source, plugin, entry)

    def _checked(
        self, source: dict[str, Any], plugin: dict[str, Any], entry: dict[str, Any]
    ) -> bytes:
        prefix = f"{plugin['path']}/" if plugin["path"] else ""
        data = self._raw(source["repo"], source["commit"], prefix + entry["path"])
        if _git_blob_sha(data) != entry["sha"]:
            raise SkillCatalogError(f"{entry['path']} didn't match what the source listed")
        return data

    def install(self, skills_dir: Path, plugin_id: str) -> list[str]:
        """Downloads the plugin whole into `<skills_dir>/<name>`; returns its skills' names."""
        source, plugin = self.plugin(plugin_id)
        root = Path(skills_dir)
        root.mkdir(parents=True, exist_ok=True)
        target = root / plugin["name"]
        if target.exists():
            raise SkillCatalogError(f"A plugin or skill named {plugin['name']!r} is already added")
        if sum(f["size"] for f in plugin["files"]) > _PLUGIN_MAX_BYTES:
            raise SkillCatalogError(f"{plugin['name']} is over 50 MB")
        staging = Path(tempfile.mkdtemp(prefix=f".{plugin['name']}-", dir=root))
        try:
            for entry in plugin["files"]:
                dest = (staging / entry["path"]).resolve()
                if not dest.is_relative_to(staging.resolve()):
                    raise SkillCatalogError(f"Unsafe path in the source: {entry['path']}")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(self._checked(source, plugin, entry))
            (staging / SOURCE_MARKER).write_text(
                json.dumps(
                    {"repo": source["repo"], "commit": source["commit"], "plugin": plugin["name"]}
                ),
                encoding="utf-8",
            )
            staging.rename(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        return [s.name for s in load_skills(root) if s.plugin_dir == target or s.dir == target]
