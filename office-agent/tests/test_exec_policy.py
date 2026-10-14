"""Tests for runtime_lg/exec_policy.py -- ROADMAP.md's Phase 7 item 2.
Pure unit tests against load_exec_policy/ExecPolicy directly; the real
wiring into web/session.py's _decide_action_request (forbidden/allow/
prompt precedence against plan mode) is covered end-to-end in
tests/test_web.py instead, since that's where a real turn/approval flow
already exists to exercise it through."""

from __future__ import annotations

import codecs
import json
import logging
from pathlib import Path

import pytest

from coscribe.runtime_lg.exec_policy import ExecPolicy, load_exec_policy


def _write_policy(path: Path, rules: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"rules": rules}), encoding="utf-8")
    return path


def test_no_path_configured_always_prompts() -> None:
    policy = load_exec_policy(None)
    assert policy.decide("import os") == ("prompt", None)


def test_missing_file_always_prompts(tmp_path: Path) -> None:
    policy = load_exec_policy(tmp_path / "does-not-exist.json")
    assert policy.decide("import os") == ("prompt", None)


def test_first_matching_rule_wins(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json",
        [
            {"pattern": r"subprocess", "decision": "prompt"},
            {"pattern": r"import", "decision": "allow"},
        ],
    )
    policy = load_exec_policy(policy_path)
    assert policy.decide("import subprocess") == ("prompt", None)
    assert policy.decide("import pandas") == ("allow", None)


def test_no_rule_matches_falls_back_to_prompt(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json", [{"pattern": r"nope", "decision": "allow"}]
    )
    policy = load_exec_policy(policy_path)
    assert policy.decide("print('hi')") == ("prompt", None)


def test_justification_is_returned_with_the_matching_decision(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json",
        [{"pattern": r"rm -rf", "decision": "forbidden", "justification": "no bulk deletes"}],
    )
    policy = load_exec_policy(policy_path)
    assert policy.decide("os.system('rm -rf /tmp/x')") == ("forbidden", "no bulk deletes")


def test_a_rule_with_no_justification_returns_none_not_an_empty_string(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json", [{"pattern": r"print", "decision": "allow"}]
    )
    policy = load_exec_policy(policy_path)
    assert policy.decide("print('hi')") == ("allow", None)


def test_malformed_json_falls_back_to_an_empty_policy_not_an_error(tmp_path: Path) -> None:
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text("not valid json", encoding="utf-8")
    policy = load_exec_policy(policy_path)
    assert policy.decide("anything") == ("prompt", None)


def test_a_json_file_without_a_rules_array_falls_back_to_an_empty_policy(tmp_path: Path) -> None:
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text(json.dumps({"not_rules": []}), encoding="utf-8")
    policy = load_exec_policy(policy_path)
    assert policy.decide("anything") == ("prompt", None)


def test_a_rule_with_an_invalid_regex_is_skipped_the_rest_still_load(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json",
        [
            {"pattern": "(unclosed", "decision": "allow"},
            {"pattern": r"print", "decision": "allow"},
        ],
    )
    policy = load_exec_policy(policy_path)
    assert policy.decide("print('hi')") == ("allow", None)


def test_a_rule_with_an_invalid_decision_is_skipped(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json", [{"pattern": r"print", "decision": "yolo-allow-everything"}]
    )
    policy = load_exec_policy(policy_path)
    assert policy.decide("print('hi')") == ("prompt", None)


def test_a_rule_missing_pattern_is_skipped(tmp_path: Path) -> None:
    policy_path = _write_policy(tmp_path / "exec_policy.json", [{"decision": "allow"}])
    policy = load_exec_policy(policy_path)
    assert policy.decide("anything") == ("prompt", None)


def test_a_non_object_rule_entry_is_skipped(tmp_path: Path) -> None:
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text(json.dumps({"rules": ["not-an-object"]}), encoding="utf-8")
    policy = load_exec_policy(policy_path)
    assert policy.decide("anything") == ("prompt", None)


def test_pattern_matches_anywhere_in_the_script_not_just_at_the_start(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json", [{"pattern": r"shutil\.rmtree", "decision": "forbidden"}]
    )
    policy = load_exec_policy(policy_path)
    script = "import shutil\nfor d in dirs:\n    shutil.rmtree(d)\n"
    assert policy.decide(script) == ("forbidden", None)


def test_empty_exec_policy_always_prompts() -> None:
    assert ExecPolicy([]).decide("anything at all") == ("prompt", None)


# -- what a broken file or rule says, and what stops there --


def _warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno == logging.WARNING]


def test_an_unparseable_file_is_logged_with_its_path_and_the_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text("not valid json", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        load_exec_policy(policy_path)

    (record,) = _warnings(caplog)
    assert record.getMessage() == f"Failed to read exec policy file {str(policy_path)!r}"
    assert record.exc_info is not None and record.exc_info[0] is json.JSONDecodeError


def test_a_file_that_is_not_a_rules_object_is_logged_with_its_path(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text(json.dumps({"rules": "allow everything"}), encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        load_exec_policy(policy_path)

    (record,) = _warnings(caplog)
    assert record.getMessage() == (
        f"Exec policy file {str(policy_path)!r} must be a JSON object with a 'rules' array "
        "-- ignoring it"
    )


def test_each_kind_of_bad_rule_is_logged_by_position_and_the_good_ones_still_load(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    policy_path = tmp_path / "exec_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "rules": [
                    "not-an-object",
                    {"decision": "allow"},
                    {"pattern": "", "decision": "allow"},
                    {"pattern": 5, "decision": "allow"},
                    {"pattern": "second", "decision": "yolo"},
                    {"pattern": "(unclosed", "decision": "allow"},
                    {"pattern": "first", "decision": "forbidden", "justification": "never"},
                    {"pattern": "last", "decision": "allow"},
                ]
            }
        ),
        encoding="utf-8",
    )
    where = str(policy_path)

    with caplog.at_level(logging.WARNING):
        policy = load_exec_policy(policy_path)

    records = _warnings(caplog)
    assert [r.getMessage() for r in records] == [
        f"Exec policy rule 0 in {where!r} is not an object -- skipping",
        f"Exec policy rule 1 in {where!r} has no string 'pattern' -- skipping",
        f"Exec policy rule 2 in {where!r} has no string 'pattern' -- skipping",
        f"Exec policy rule 3 in {where!r} has no string 'pattern' -- skipping",
        f"Exec policy rule 4 in {where!r} has invalid decision 'yolo' -- skipping",
        f"Exec policy rule 5 in {where!r} has an invalid regex '(unclosed' -- skipping",
    ]
    assert records[-1].exc_info is not None and records[-1].exc_info[0] is not None
    assert policy.decide("a first b") == ("forbidden", "never")
    assert policy.decide("a last b") == ("allow", None)
    assert policy.decide("yolo second") == ("prompt", None)


def test_an_empty_pattern_is_skipped_rather_than_matching_every_script(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json", [{"pattern": "", "decision": "allow"}]
    )

    assert load_exec_policy(policy_path).decide("anything at all") == ("prompt", None)


def test_a_rule_without_a_decision_prompts_and_shadows_the_later_rules(tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json",
        [{"pattern": "print"}, {"pattern": "print", "decision": "allow"}],
    )

    assert load_exec_policy(policy_path).decide("print('hi')") == ("prompt", None)


@pytest.mark.parametrize("justification", [5, ["a reason"], {"why": "x"}, None])
def test_a_justification_that_is_not_text_is_dropped(justification: object, tmp_path: Path) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json",
        [{"pattern": "print", "decision": "allow", "justification": justification}],
    )

    assert load_exec_policy(policy_path).decide("print('hi')") == ("allow", None)


def test_the_policy_file_is_read_as_utf8_whatever_the_locale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_path = _write_policy(
        tmp_path / "exec_policy.json",
        [{"pattern": "删除", "decision": "forbidden", "justification": "不要删除"}],
    )
    seen: list[str | None] = []
    real_read = Path.read_text

    def read_text(self: Path, encoding: str | None = None, errors: str | None = None) -> str:
        seen.append(encoding)
        return real_read(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", read_text)

    policy = load_exec_policy(policy_path)

    assert seen and all(e is not None and codecs.lookup(e).name == "utf-8" for e in seen)
    assert policy.decide("请删除文件") == ("forbidden", "不要删除")
