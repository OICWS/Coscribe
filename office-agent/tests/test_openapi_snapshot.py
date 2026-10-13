"""The HTTP API's request and response shapes, pinned like the route list.

`tests/web_routes.txt` says which routes exist; this says what they accept and return. The
frontend depends on those shapes, and splitting `web/app.py` moves the code that defines them,
so a change to a request or response model must show up as a readable diff in the PR that makes
it. `UPDATE_SNAPSHOTS=1 pytest tests/test_openapi_snapshot.py` rewrites `tests/openapi.json`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from coscribe.config import Settings
from coscribe.web.app import create_app_lg

SNAPSHOT = Path(__file__).with_name("openapi.json")


def _document(tmp_path: Path) -> str:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        default_model="fake:model",
        workspace_root=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        skills_dir=tmp_path / "skills",
        memory_path=tmp_path / "MEMORY.md",
    )
    # sort_keys: a dict's order follows the order routes and fields are registered in, which a
    # file split changes without changing the API.
    return json.dumps(create_app_lg(settings).openapi(), indent=2, sort_keys=True) + "\n"


def test_the_openapi_document_is_the_checked_in_one(tmp_path: Path) -> None:
    document = _document(tmp_path)
    if os.environ.get("UPDATE_SNAPSHOTS"):
        SNAPSHOT.write_text(document, encoding="utf-8", newline="\n")

    assert document == SNAPSHOT.read_bytes().decode("utf-8")
