"""Showing a file in the file manager."""

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from coscribe.conversation import activity


def test_show_in_folder_on_windows_quotes_only_the_path(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[Any] = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "Popen", lambda command: started.append(command))

    activity.open_in_os(Path("C:/Users/me/OneDrive - Bosch/A/deck.pptx"), reveal=True)

    assert started == [f'explorer /select,"{Path("C:/Users/me/OneDrive - Bosch/A/deck.pptx")}"']
