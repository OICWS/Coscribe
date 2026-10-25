"""The tool that lets a conversation find what earlier conversations made. The registry is the
Artifacts page's, so it lives here, above the tools package, and the session adds the tool beside
the others it builds."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..runtime import tool_metadata
from ..tools import WorkspaceScope
from .artifacts import ArtifactRegistry, describe_artifact

_KINDS = ("docs", "slides", "sheets", "design")
_MAX_LISTED = 50


def build_artifact_tools(
    state_dir: str | Path, scope: Callable[[], WorkspaceScope]
) -> list[Callable[..., Any]]:
    """`list_artifacts`, read only. Deferred like the other non-core tools, so the fixed tool
    list (0001) is unchanged."""
    registry = ArtifactRegistry(state_dir)

    def list_artifacts(
        kind: str | None = None, query: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """List the Word documents, presentations, workbooks and designs the user has made with
        coscribe in any conversation, newest first. Call it only when the user refers to
        something they made before and you do not have its path; never to look around, and not
        for files in this conversation's own folders (use list_files for those). A file with
        "readable": true can be opened with the usual read tools at its "path"; one with false
        lies in folders this conversation was not given, so say so instead of guessing.

        Args:
            kind: only this kind: docs, slides, sheets or design.
            query: only names containing this text, ignoring case.
            limit: how many to return, at most 50.
        """
        mine = scope()
        wanted = (query or "").strip().lower()
        found = []
        for entry in registry.entries():
            folders = [Path(f) for f in entry.get("folders", [])]
            if not folders:
                continue
            owned = WorkspaceScope(
                folders[0], extra_readable=folders[1:], extra_writable=folders[1:]
            )
            file = describe_artifact(owned, entry["location"])
            if (
                file is None
                or (kind and file["kind"] != kind)
                or wanted not in file["name"].lower()
            ):
                continue
            try:
                path, readable = mine.relative(mine.resolve(file["location"])), True
            except (PermissionError, OSError, ValueError):
                path, readable = file["location"], False
            heading = (file["excerpt"] or {}).get("heading")
            found.append(
                {
                    "name": file["name"],
                    "kind": file["kind"],
                    "path": path,
                    "readable": readable,
                    "modified_at": file["modified_at"],
                    **({"heading": heading} if heading else {}),
                }
            )
        found.sort(key=lambda item: item["modified_at"], reverse=True)
        return found[: max(1, min(limit, _MAX_LISTED))]

    return [tool_metadata(list_artifacts, risk_category="READ", category="documents")]
