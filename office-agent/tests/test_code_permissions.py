"""Settings > Code's per-action policy (code_runtime/permissions.py): what is stored, what a
missing or damaged file means, and what an update refuses."""

from __future__ import annotations

import codecs
import json
from pathlib import Path
from typing import Any

import pytest

from coscribe.code_runtime.permissions import CodePermissions

ACTIONS = ("code_command", "code_file_change")


def test_code_permissions_default_to_ask_when_nothing_is_stored(tmp_path: Path) -> None:
    permissions = CodePermissions(tmp_path, ACTIONS)

    assert permissions.load() == {"code_command": "ask", "code_file_change": "ask"}
    assert permissions.policy("code_command") == "ask"


@pytest.mark.parametrize("content", ["not json", "[]", '"allow"', "null", '{"code_command": 7}'])
def test_code_permissions_treat_a_damaged_file_as_ask(tmp_path: Path, content: str) -> None:
    (tmp_path / "code_permissions.json").write_text(content, encoding="utf-8")

    assert CodePermissions(tmp_path, ACTIONS).load() == {
        "code_command": "ask",
        "code_file_change": "ask",
    }


def test_code_permissions_keep_what_is_stored_and_ignore_what_is_not_an_action(
    tmp_path: Path,
) -> None:
    (tmp_path / "code_permissions.json").write_text(
        json.dumps({"code_command": "allow", "code_file_change": "maybe", "stray": "allow"}),
        encoding="utf-8",
    )
    permissions = CodePermissions(tmp_path, ACTIONS)

    assert permissions.load() == {"code_command": "allow", "code_file_change": "ask"}
    assert permissions.policy("code_command") == "allow"
    assert permissions.policy("code_file_change") == "ask"
    assert permissions.policy("not_an_action") == "ask"


def test_code_permissions_update_merges_and_writes_a_readable_file(tmp_path: Path) -> None:
    permissions = CodePermissions(tmp_path / "state" / "nested", ACTIONS)

    assert permissions.update({"code_command": "allow"}) == {
        "code_command": "allow",
        "code_file_change": "ask",
    }
    assert permissions.update({"code_file_change": "allow"}) == {
        "code_command": "allow",
        "code_file_change": "allow",
    }
    assert permissions.update({"code_command": "ask"}) == {
        "code_command": "ask",
        "code_file_change": "allow",
    }

    written = (tmp_path / "state" / "nested" / "code_permissions.json").read_text(encoding="utf-8")
    assert written == json.dumps({"code_command": "ask", "code_file_change": "allow"}, indent=2)
    assert permissions.policy("code_file_change") == "allow"


def test_code_permissions_update_says_what_it_expected_and_writes_nothing(
    tmp_path: Path,
) -> None:
    permissions = CodePermissions(tmp_path, ACTIONS)

    with pytest.raises(ValueError) as unknown_and_bad:
        permissions.update({"rm_rf": "allow", "code_command": "always"})

    assert str(unknown_and_bad.value) == (
        "Expected code_command/code_file_change set to ask/allow: rm_rf, code_command: 'always'"
    )
    with pytest.raises(ValueError) as bad_only:
        permissions.update({"code_file_change": 1})  # type: ignore[dict-item]
    assert str(bad_only.value) == (
        "Expected code_command/code_file_change set to ask/allow: code_file_change: 1"
    )
    assert not (tmp_path / "code_permissions.json").exists()


def test_code_permissions_file_is_read_and_written_as_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str | None] = []
    real_read, real_write = Path.read_text, Path.write_text

    def read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        seen.append(kwargs.get("encoding"))
        return real_read(self, *args, **kwargs)

    def write_text(self: Path, data: str, *args: Any, **kwargs: Any) -> int:
        seen.append(kwargs.get("encoding"))
        return real_write(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(Path, "write_text", write_text)

    permissions = CodePermissions(tmp_path, ACTIONS)
    permissions.update({"code_command": "allow"})
    permissions.load()

    assert len(seen) == 3
    assert all(e is not None and codecs.lookup(e).name == "utf-8" for e in seen), seen
