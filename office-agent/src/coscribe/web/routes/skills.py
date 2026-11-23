"""Skills routes."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    UploadFile,
)
from fastapi.responses import JSONResponse

from ...tools import (
    SKILL_SOURCE_MARKER,
    PluginSources,
    SkillCatalogError,
    SkillInfo,
    SkillUploadError,
    WorkspaceScope,
    all_skills,
    disabled_skill_names,
    get_plugin,
    install_plugin,
    load_builtin_skills,
    load_catalog,
    plugin_file,
    remove_skill,
    save_uploaded_skill,
    set_skill_enabled,
    skill_source,
)
from ..schemas import (
    PluginSourceAdd,
    SkillEnabledUpdate,
)
from ..state import AppState
from .shared import MAX_UPLOAD_BYTES


def _skill_row(skill: SkillInfo, source: str, enabled: bool) -> dict[str, Any]:
    updated = datetime.fromtimestamp((skill.dir / "SKILL.md").stat().st_mtime, UTC)
    return {
        "name": skill.name,
        "description": skill.description,
        "source": source,
        "enabled": enabled,
        "updated": updated.isoformat(),
        "plugin": skill.plugin,
        "plugin_info": skill.plugin_info(),
    }


def _source_plugin(source: dict[str, Any], plugin: dict[str, Any]) -> dict[str, Any]:
    """A plugin of a source the person added, shaped as Discover's catalog shapes its own."""
    owner, name = source["repo"].split("/", 1)
    return {
        **{key: plugin[key] for key in ("title", "author", "version", "description", "skills")},
        "id": f"gh:{owner}:{name}:{plugin['name']}",
        "repo": source["repo"],
        "license": "",
        "updated": source["updated"][:10],
        "files": plugin["files"],
        "source": source["repo"],
    }


def _find_plugin(state_dir: Path, plugin_id: str) -> dict[str, Any]:
    if not plugin_id.startswith("gh:"):
        return get_plugin(plugin_id)
    return _source_plugin(*PluginSources(state_dir).plugin(plugin_id))


def _plugin_file(state_dir: Path, plugin: dict[str, Any], path: str) -> bytes:
    if plugin.get("source"):
        return PluginSources(state_dir).file(plugin["id"], path)
    return plugin_file(plugin["id"], path)


def _install_plugin(state_dir: Path, skills_dir: Path, plugin_id: str) -> list[str]:
    if plugin_id.startswith("gh:"):
        return PluginSources(state_dir).install(skills_dir, plugin_id)
    return install_plugin(skills_dir, plugin_id)


def _source_routes(router: APIRouter, state: AppState) -> None:
    """A source the person adds to Discover: a GitHub repository with a marketplace.json."""

    def sources() -> PluginSources:
        return PluginSources(state.settings.state_dir)

    async def list_sources() -> list[dict[str, Any]]:
        return [_source_row(s) for s in sources().sources()]

    async def add_source(payload: PluginSourceAdd) -> JSONResponse:
        try:
            source = await asyncio.to_thread(sources().add, payload.address)
        except SkillCatalogError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(_source_row(source))

    async def remove_source(repo: str) -> JSONResponse:
        try:
            sources().remove(repo)
        except SkillCatalogError:
            return JSONResponse({"error": f"{repo!r} isn't a source"}, status_code=404)
        return JSONResponse({"removed": repo})

    router.add_api_route("/api/skills/sources", list_sources, methods=["GET"])
    router.add_api_route("/api/skills/sources", add_source, methods=["POST"])
    router.add_api_route("/api/skills/sources/{repo:path}", remove_source, methods=["DELETE"])


def _source_row(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo": source["repo"],
        "name": source["name"],
        "commit": source["commit"],
        "updated": source["updated"],
        "plugins": len(source["plugins"]),
        "elsewhere": source["elsewhere"],
    }


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _source_routes(router, state)
    _skills_by_name = state.skills_by_name

    @router.get("/api/skills")
    async def get_skills() -> list[dict[str, Any]]:
        builtin_names = {skill.name for skill in load_builtin_skills()}
        disabled = disabled_skill_names(settings.state_dir)
        return [
            _skill_row(skill, skill_source(skill, builtin_names), skill.name not in disabled)
            for skill in all_skills(settings.skills_dir)
        ]

    @router.post("/api/skills/{name}/enabled")
    async def update_skill_enabled(name: str, payload: SkillEnabledUpdate) -> JSONResponse:
        if name not in _skills_by_name():
            return JSONResponse({"error": f"No skill named {name!r}."}, status_code=404)
        set_skill_enabled(settings.state_dir, name, payload.enabled)
        return JSONResponse({"name": name, "enabled": payload.enabled})

    @router.delete("/api/skills/{name}")
    async def delete_skill(name: str, plugin: bool = False) -> JSONResponse:
        try:
            removed = await asyncio.to_thread(
                remove_skill, settings.skills_dir, settings.state_dir, name, plugin=plugin
            )
        except SkillCatalogError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse({"removed": name, "skills": removed})

    _SKILL_FILE_PREVIEW_MAX_BYTES = 500_000

    def _plugin_summary(plugin: dict[str, Any]) -> dict[str, Any]:
        installed = set(_skills_by_name())
        return {
            "id": plugin["id"],
            "title": plugin["title"],
            "author": plugin["author"],
            "repo": plugin["repo"],
            "version": plugin["version"],
            "description": plugin["description"],
            "license": plugin["license"],
            "updated": plugin["updated"],
            "skills": plugin["skills"],
            "added": sum(1 for n in plugin["skills"] if n in installed),
            "source": plugin.get("source"),
        }

    @router.get("/api/skills/plugins")
    async def get_skill_plugins() -> list[dict[str, Any]]:
        sources = PluginSources(settings.state_dir).sources()
        added = [_source_plugin(s, p) for s in sources for p in s["plugins"]]
        return [_plugin_summary(p) for p in [*load_catalog()["plugins"], *added]]

    @router.get("/api/skills/plugins/{plugin_id}")
    async def get_skill_plugin(plugin_id: str) -> JSONResponse:
        try:
            plugin = _find_plugin(settings.state_dir, plugin_id)
        except SkillCatalogError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        descriptions = {s["name"]: s["description"] for s in load_catalog()["skills"]}
        return JSONResponse(
            {
                **_plugin_summary(plugin),
                "files": [f["path"] for f in plugin["files"]],
                "skill_details": [
                    {"name": n, "description": descriptions.get(n, "")} for n in plugin["skills"]
                ],
            }
        )

    @router.get("/api/skills/plugins/{plugin_id}/files/{path:path}")
    async def get_skill_plugin_file(plugin_id: str, path: str) -> JSONResponse:
        try:
            plugin = _find_plugin(settings.state_dir, plugin_id)
        except SkillCatalogError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        entry = next((f for f in plugin["files"] if f["path"] == path), None)
        if entry is None:
            return JSONResponse({"error": f"No such file: {path!r}."}, status_code=404)
        if entry["size"] > _SKILL_FILE_PREVIEW_MAX_BYTES:
            return JSONResponse(
                {"error": f"File is {entry['size']:,} bytes -- too large to preview here."},
                status_code=413,
            )
        try:
            data = await asyncio.to_thread(_plugin_file, settings.state_dir, plugin, path)
            return JSONResponse({"path": path, "content": data.decode("utf-8")})
        except UnicodeDecodeError:
            return JSONResponse(
                {"error": "This file isn't UTF-8 text -- can't preview it here."}, status_code=415
            )
        except SkillCatalogError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)

    @router.post("/api/skills/plugins/{plugin_id}")
    async def add_skill_plugin(plugin_id: str) -> JSONResponse:
        try:
            added = await asyncio.to_thread(
                _install_plugin, settings.state_dir, settings.skills_dir, plugin_id
            )
        except SkillCatalogError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        for name in added:
            set_skill_enabled(settings.state_dir, name, True)
        return JSONResponse({"added": added})

    @router.get("/api/skills/{name}/files")
    async def get_skill_files(name: str) -> JSONResponse:
        # Backs the Skills settings tab's own file-tree browser (a skill
        # is a real directory -- SKILL.md plus whatever reference docs/
        # scripts it needs -- so "click a skill to see its folder" is a
        # real filesystem listing, not a database query). Flat list of
        # relative posix paths, same shape files.py's own list_files tool
        # already returns -- the frontend folds path segments into a tree
        # client-side rather than this endpoint building nested JSON.
        skill = _skills_by_name().get(name)
        if skill is None:
            return JSONResponse({"error": f"No skill named {name!r}."}, status_code=404)
        files = sorted(
            path.relative_to(skill.dir).as_posix()
            for path in skill.dir.rglob("*")
            if path.is_file() and path.name != SKILL_SOURCE_MARKER
        )
        return JSONResponse({"files": files})

    # A skill's own files are typically short prose/scripts meant to be
    # read whole, not paginated -- this cap exists only to stop a genuinely
    # huge file (an accidentally-included data dump) from being sent whole
    # to the browser, matching search_files/list_files' own "bounded, not
    # unlimited" caps elsewhere in this codebase.

    @router.get("/api/skills/{name}/files/{path:path}")
    async def get_skill_file_content(name: str, path: str) -> JSONResponse:
        skill = _skills_by_name().get(name)
        if skill is None:
            return JSONResponse({"error": f"No skill named {name!r}."}, status_code=404)
        scope = WorkspaceScope(skill.dir)
        try:
            file_path = scope.resolve(path)
        except PermissionError:
            return JSONResponse(
                {"error": "Path is outside this skill's own directory."}, status_code=400
            )
        if not file_path.is_file():
            return JSONResponse({"error": f"No such file: {path!r}."}, status_code=404)
        size = file_path.stat().st_size
        if size > _SKILL_FILE_PREVIEW_MAX_BYTES:
            return JSONResponse(
                {"error": f"File is {size:,} bytes -- too large to preview here."}, status_code=413
            )
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return JSONResponse(
                {"error": "This file isn't UTF-8 text -- can't preview it here."}, status_code=415
            )
        return JSONResponse({"path": path, "content": content})

    @router.post("/api/skills/upload")
    async def upload_skill(file: UploadFile) -> JSONResponse:
        # The real half of Settings > Skills > Add > Upload skill (see
        # tools/skills.py's save_uploaded_skill for the accepted shapes).
        # Always writes into settings.skills_dir, i.e.
        # always a "custom" skill -- there's no UI path to add a builtin
        # one, those only ever come from the package itself.
        content = await file.read()
        if len(content) > MAX_UPLOAD_BYTES:
            return JSONResponse({"error": "file too large (max 25MB)"}, status_code=413)
        try:
            skill = save_uploaded_skill(settings.skills_dir, file.filename or "", content)
        except SkillUploadError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(_skill_row(skill, "custom", True))

    return router
