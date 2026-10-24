"""Named environments (runtime/environments.py): what an environment holds and refuses, which
conversation uses which, and the move of each conversation's own settings into environments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from coscribe.runtime import (
    DEFAULT_ENVIRONMENT,
    EnvironmentRefused,
    Environments,
    NetworkAccess,
    SessionEnvironments,
)
from coscribe.tools.exec import CapabilityOff, require_capability


def _refusal(
    environments: Environments, fields: dict[str, Any], known: frozenset[str] = frozenset()
) -> str:
    with pytest.raises(EnvironmentRefused) as raised:
        environments.create({"name": "E", **fields}, set(known))
    return str(raised.value)


def test_every_conversation_uses_default_until_it_chooses_another(tmp_path: Path) -> None:
    environments = Environments(tmp_path)
    reports = environments.create({"name": "Reports", "variables": {"MODE": "fast"}}, set())

    environments.assign("t1", reports["id"])

    assert environments.environment_of("t1") == reports["id"]
    assert environments.environment_of("t2") == environments.environment_of(None) == "default"
    assert SessionEnvironments(tmp_path).get("t1")["variables"] == {"MODE": "fast"}
    assert SessionEnvironments(tmp_path).get("t2") == {"variables": {}, "secrets": []}
    assert NetworkAccess(tmp_path).get("t2") == {"mode": "limited", "domains": ["*"]}
    assert [(e["name"], e["used_by"]) for e in environments.all()] == [
        ("Default", 0),
        ("Reports", 1),
    ]


def test_deleting_an_environment_moves_its_conversations_to_default_which_stays(
    tmp_path: Path,
) -> None:
    environments = Environments(tmp_path)
    doomed = environments.create({"name": "Doomed"}, set())
    environments.assign("t1", doomed["id"])

    assert environments.delete(doomed["id"]) == ["t1"]
    assert environments.environment_of("t1") == DEFAULT_ENVIRONMENT
    with pytest.raises(EnvironmentRefused, match="Default can't be deleted"):
        environments.delete(DEFAULT_ENVIRONMENT)
    with pytest.raises(KeyError):
        environments.delete(doomed["id"])
    with pytest.raises(KeyError):
        environments.assign("t1", doomed["id"])


def test_what_an_environment_refuses(tmp_path: Path) -> None:
    environments = Environments(tmp_path)
    environments.create({"name": "Taken"}, set())

    assert _refusal(environments, {"name": " "}) == (
        "Give the environment a name of up to 60 characters."
    )
    assert _refusal(environments, {"name": "taken"}) == (
        "There is already an environment named Taken."
    )
    assert _refusal(environments, {"variables": []}) == (
        "variables must be a map of names to text values."
    )
    assert _refusal(environments, {"variables": {f"V{i}": "1" for i in range(101)}}) == (
        "At most 100 variables."
    )
    assert _refusal(environments, {"variables": {"bad name": "1"}}) == (
        "'bad name' isn't a variable name: letters, digits and underscores."
    )
    assert _refusal(environments, {"variables": {"X": "y" * 4097}}) == (
        "The value of X is longer than 4096 characters."
    )
    assert _refusal(environments, {"secrets": "AB"}) == "secrets must be a list of secret names."
    assert _refusal(environments, {"secrets": ["A", "B", "C"]}, frozenset({"C"})) == (
        "No such secret: A, B."
    )
    assert _refusal(environments, {"variables": {"A": "1"}, "secrets": ["A"]}, frozenset("A")) == (
        "A is both a variable and a secret; keep one."
    )
    assert "isn't an existing folder" in _refusal(environments, {"folders": [str(tmp_path / "x")]})
    assert "Limited needs at least one domain" in _refusal(
        environments, {"network": {"mode": "limited", "domains": []}}
    )
    assert _refusal(environments, {"commands": "yes"}) == "commands must be true or false."
    assert [e["name"] for e in environments.all()] == ["Default", "Taken"]


def test_an_edit_keeps_the_fields_it_does_not_name(tmp_path: Path) -> None:
    environments = Environments(tmp_path)
    made = environments.create(
        {"name": "Mine", "folders": [str(tmp_path)], "variables": {"LABEL": "名称"}}, set()
    )

    changed = environments.update(made["id"], {"commands": False}, set())

    assert changed["folders"] == [str(tmp_path)] and changed["variables"] == {"LABEL": "名称"}
    assert changed["commands"] is False
    assert "名称" in (tmp_path / "environments.json").read_bytes().decode("utf-8")
    assert not list(tmp_path.glob("*.tmp"))


def test_an_unreadable_file_leaves_only_default(tmp_path: Path) -> None:
    (tmp_path / "environments.json").write_text("{not json", encoding="utf-8")
    assert [e["id"] for e in Environments(tmp_path).all()] == ["default"]
    (tmp_path / "environments.json").write_text(
        json.dumps(
            {"environments": {"e1": {"name": "Odd", "network": "x"}}, "threads": {"t1": "gone"}}
        ),
        encoding="utf-8",
    )
    odd = Environments(tmp_path).get("e1")
    assert odd is not None and odd["network"] == {"mode": "limited", "domains": ["*"]}
    assert Environments(tmp_path).environment_of("t1") == "default"


def test_an_environment_turns_off_what_settings_allow_but_never_turns_on_more(
    tmp_path: Path,
) -> None:
    environments = Environments(tmp_path)
    no_scripts = environments.create({"name": "No scripts", "scripts": False}, set())
    environments.assign("t1", no_scripts["id"])

    with pytest.raises(CapabilityOff, match=r"environment \(No scripts\) doesn't allow scripts"):
        require_capability(tmp_path, "scripts", "t1")
    require_capability(tmp_path, "scripts", "t2")
    with pytest.raises(CapabilityOff, match="Settings › Capabilities"):
        require_capability(tmp_path, "commands", "t2")


def test_a_folder_allowed_on_default_makes_an_environment_and_on_another_joins_it(
    tmp_path: Path,
) -> None:
    environments = Environments(tmp_path)
    environments.create({"name": "Invoices"}, set())

    environments.add_folders("t1", ["/a", "/b"], "Invoices")
    own = environments.environment_of("t1")
    environments.add_folders("t1", ["/a", "/b", "/c"], "ignored")

    assert environments.environment_of("t1") == own != DEFAULT_ENVIRONMENT
    assert environments.for_thread(None)["folders"] == []
    assert environments.for_thread("t1")["name"] == "Invoices (2)"
    assert environments.for_thread("t1")["folders"] == ["/a", "/b", "/c"]


def test_the_move_groups_conversations_with_the_same_settings_and_runs_once(
    tmp_path: Path,
) -> None:
    environments = Environments(tmp_path)
    same = {"folders": ["/shared"]}
    environments.migrate(
        {
            "t1": same,
            "t2": dict(same),
            "t3": {"network": {"mode": "none", "domains": []}},
            "t4": {"network": {"mode": "limited", "domains": ["*"]}},
        },
        {"t1": "  A   long\n title  ", "t3": "A long title"},
    )
    environments.migrate({"t5": same}, {})

    named = {e["name"]: e for e in environments.all()}
    assert sorted(named) == ["A long title", "A long title (2)", "Default"]
    assert named["A long title"]["used_by"] == 2
    assert environments.environment_of("t3") == named["A long title (2)"]["id"]
    assert environments.environment_of("t4") == environments.environment_of("t5") == "default"
