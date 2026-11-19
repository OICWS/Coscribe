"""A folder asked for from the chat (conversation/folder_access.py, decision 0048): what is
offered, what Allow writes into Settings' Allowed folders, and what the model is told."""

from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values

from coscribe.config import Settings
from coscribe.conversation.folder_access import (
    add_allowed_folder,
    checked_folder,
    result_message,
)


def test_a_comma_in_the_path_is_not_offered(tmp_path: Path) -> None:
    folder = tmp_path / "Smith, John"
    folder.mkdir()
    offered, why = checked_folder(str(folder))
    assert offered is None
    assert "comma" in why


def test_allow_keeps_what_settings_wrote_since_the_server_started(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    earlier, added_in_settings, allowed = (tmp_path / n for n in ("A", "B", "C"))
    env_file.write_text(f"COSCRIBE_EXTRA_READABLE_DIRS={earlier}, {added_in_settings}\n")
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None, default_model="fake:model", extra_readable_dirs=[earlier]
    )

    add_allowed_folder(settings, allowed, "read", env_file)

    saved = dotenv_values(env_file)["COSCRIBE_EXTRA_READABLE_DIRS"]
    assert saved == f"{earlier}, {added_in_settings}, {allowed}"
    assert settings.extra_readable_dirs == [earlier, allowed]


def test_less_access_than_asked_says_so() -> None:
    message = result_message("chat", Path("/x"), "read", "chat:read", "read-write")
    assert "reading only" in message
    assert "Call the refused tool again" not in message
