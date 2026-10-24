"""Taking coscribe's folder grants (tools/exec/isolation.py) off folders no longer in use: at
each start, for a folder the person removed from Settings and every conversation, and all of
them at uninstall (`--revoke-folder-grants`, which the installer runs)."""

from __future__ import annotations

import logging
from pathlib import Path

from ..config import Settings
from ..runtime import Environments
from ..tools import SCHEDULED_THREAD_PREFIX, sweep_folder_grants
from .thread_files import ThreadFiles


def folders_in_use(settings: Settings) -> list[Path]:
    threads = ThreadFiles(settings)
    folders = [
        settings.workspace_root,
        settings.skills_dir,
        *settings.extra_readable_dirs,
        *settings.extra_writable_dirs,
        *settings.extra_deletable_dirs,
    ]
    for env in Environments(settings.state_dir).all():
        folders.extend(Path(f) for f in env["folders"])
    for sidecar in settings.state_dir.glob(f"{SCHEDULED_THREAD_PREFIX}*.workspace"):
        folders.extend(Path(f) for f in threads.folders_of(sidecar.stem))
    return folders


def sweep_unused_folder_grants(settings: Settings) -> None:
    swept = sweep_folder_grants(settings.state_dir, folders_in_use(settings))
    if swept:
        logging.getLogger(__name__).info("Took scripts' access off %d folder(s).", len(swept))
