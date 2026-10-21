"""The Artifacts page's list: the decks, documents and spreadsheets the conversations made."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from ...conversation import artifact_paths, describe_artifact
from ...tools import SCHEDULED_THREAD_PREFIX, WorkspaceScope
from ..state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    # Per conversation: the newest checkpoint read and the artifacts it named, so a later request
    # reads only the conversations that moved on and looks at each file again.
    named: dict[str, tuple[str, list[tuple[str, str]]]] = {}

    def scope_of(thread_id: str) -> WorkspaceScope:
        folders = [Path(f) for f in state.thread_files.read_workspace_sidecar(thread_id)]
        extra = folders[1:]
        return WorkspaceScope(
            folders[0] if folders else settings.workspace_root,
            extra_readable=[*settings.extra_readable_dirs, *extra],
            extra_writable=[*settings.extra_writable_dirs, *extra],
        )

    async def list_artifacts() -> list[dict[str, Any]]:
        # Which tools write a file is known to the sessions; one of them is enough.
        session = next(iter(state.sessions.values()), None)
        if session is None:
            return []
        catalog = session.tool_catalog()
        checkpointer = state.checkpointer_holder["checkpointer"]
        await checkpointer.setup()
        cursor = await checkpointer.conn.execute(
            "SELECT thread_id, MAX(checkpoint_id) FROM checkpoints GROUP BY thread_id"
        )
        # One entry per file, from the conversation that made it, else the latest to change it.
        found: dict[str, tuple[tuple[bool, str], dict[str, Any]]] = {}
        for thread_id, latest in await cursor.fetchall():
            if thread_id.startswith(SCHEDULED_THREAD_PREFIX):
                continue
            scope = scope_of(thread_id)
            if named.get(thread_id, ("", []))[0] != latest:
                tuple_ = await checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})
                messages = (
                    list(tuple_.checkpoint["channel_values"].get("messages", [])) if tuple_ else []
                )
                named[thread_id] = (
                    latest,
                    await asyncio.to_thread(artifact_paths, messages, catalog, scope),
                )
            for path, action in named[thread_id][1]:
                artifact = describe_artifact(scope, path)
                if artifact is None:
                    continue
                rank = (action == "created", latest)
                known = found.get(artifact["location"])
                if known is None or rank > known[0]:
                    found[artifact["location"]] = (rank, {**artifact, "thread_id": thread_id})
        artifacts = [
            {k: v for k, v in artifact.items() if k != "location"} for _, artifact in found.values()
        ]
        artifacts.sort(key=lambda a: a["modified_at"], reverse=True)
        return artifacts

    router.add_api_route("/api/artifacts", list_artifacts, methods=["GET"])
    return router
