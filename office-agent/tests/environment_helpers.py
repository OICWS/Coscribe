"""Puts a test's conversation in an environment of its own with the given settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from coscribe.runtime import DEFAULT_ENVIRONMENT, Environments


def in_environment(state_dir: Path, thread_id: str, **fields: Any) -> str:
    """The id of `thread_id`'s own environment, made on the first call and changed on later ones."""
    environments = Environments(state_dir)
    known = set(fields.get("secrets", []))
    env_id = environments.environment_of(thread_id)
    if env_id != DEFAULT_ENVIRONMENT:
        environments.update(env_id, fields, known)
        return env_id
    env = environments.create({"name": thread_id, **fields}, known)
    environments.assign(thread_id, env["id"])
    return str(env["id"])
