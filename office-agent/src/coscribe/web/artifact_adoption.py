"""Registering what conversations created as artifacts (`conversation.ArtifactRegistry`), from
their checkpoints: when the Artifacts page is read, and before a conversation is deleted."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..config import Settings
from ..conversation import ArtifactRegistry, ChatSessionLG, adopt_thread
from ..tools import SCHEDULED_THREAD_PREFIX
from .thread_files import ThreadFiles


class ArtifactAdoption:
    def __init__(
        self,
        settings: Settings,
        thread_files: ThreadFiles,
        sessions: Mapping[str, ChatSessionLG],
        checkpointer_holder: Mapping[str, Any],
    ) -> None:
        self.registry = ArtifactRegistry(settings.state_dir)
        self._thread_files = thread_files
        self._sessions = sessions
        self._checkpointer_holder = checkpointer_holder
        # Per conversation, the newest checkpoint already adopted, so a later read goes through
        # only the conversations that moved on.
        self._adopted: dict[str, str] = {}

    async def adopt(self, thread_ids: list[str] | None = None) -> None:
        """What the given conversations (all of them by default) created."""
        # Which tools write a file is known to the sessions; one of them is enough.
        session = next(iter(self._sessions.values()), None)
        if session is None:
            return
        checkpointer = self._checkpointer_holder["checkpointer"]
        await checkpointer.setup()
        cursor = await checkpointer.conn.execute(
            "SELECT thread_id, MAX(checkpoint_id) FROM checkpoints GROUP BY thread_id"
        )
        for thread_id, latest in await cursor.fetchall():
            if thread_ids is not None and thread_id not in thread_ids:
                continue
            if (
                thread_id.startswith(SCHEDULED_THREAD_PREFIX)
                or self._adopted.get(thread_id) == latest
            ):
                continue
            files = self._thread_files
            await adopt_thread(
                self.registry,
                checkpointer,
                thread_id,
                session.tool_catalog(),
                files.workspace_scope(thread_id),
                [str(folder) for folder in files.workspace_folders(thread_id)],
            )
            self._adopted[thread_id] = latest
