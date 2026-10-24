"""Global secrets and per-session environments (runtime/secret_store.py): the
value goes to the keychain only, and nothing hands it back out."""

from __future__ import annotations

import base64
import codecs
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import keyring.errors
import pytest

from coscribe.runtime import (
    KeychainUnavailable,
    SecretError,
    SecretStore,
    SessionEnvironments,
    host_allowed,
    secrets,
)
from coscribe.runtime import secret_store as store_module
from tests.environment_helpers import in_environment


class _FakeKeyring:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}
        self.reads = 0
        self.unreadable: set[str] = set()
        self.errors = keyring.errors

    def set_password(self, service: str, ref: str, value: str) -> None:
        self.store[(service, ref)] = value

    def get_password(self, service: str, ref: str) -> str | None:
        self.reads += 1
        if ref in self.unreadable:
            raise keyring.errors.KeyringError("keychain locked")
        return self.store.get((service, ref))

    def delete_password(self, service: str, ref: str) -> None:
        self.store.pop((service, ref), None)


@pytest.fixture
def keychain(monkeypatch: pytest.MonkeyPatch) -> _FakeKeyring:
    fake = _FakeKeyring()
    monkeypatch.setattr(secrets, "keyring", fake)
    monkeypatch.setattr(secrets, "keychain_backend_usable", lambda: True)
    return fake


def test_a_value_goes_to_the_keychain_and_never_to_a_file(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)

    saved = store.save("STRIPE_KEY", "sk-live-123", ["api.stripe.com"])

    assert saved["name"] == "STRIPE_KEY" and saved["hosts"] == ["api.stripe.com"]
    assert "value" not in saved
    assert keychain.store == {("coscribe", "secret:STRIPE_KEY"): "sk-live-123"}
    assert "sk-live-123" not in (tmp_path / "secrets.json").read_text()
    assert "sk-live-123" not in json.dumps(store.entries())
    assert store.resolve("STRIPE_KEY") == "sk-live-123"


def test_a_machine_with_no_keychain_refuses_rather_than_write_a_plain_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(secrets, "keychain_backend_usable", lambda: False)

    with pytest.raises(KeychainUnavailable, match="never written to a plain file"):
        SecretStore(tmp_path).save("A", "value-cccc", ["example.com"])

    assert not (tmp_path / "secrets.json").exists()


def test_a_keychain_that_refuses_the_write_leaves_no_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Refusing(_FakeKeyring):
        def set_password(self, service: str, ref: str, value: str) -> None:
            raise keyring.errors.PasswordSetError("locked")

    monkeypatch.setattr(secrets, "keyring", Refusing())
    monkeypatch.setattr(secrets, "keychain_backend_usable", lambda: True)

    with pytest.raises(KeychainUnavailable):
        SecretStore(tmp_path).save("A", "value-cccc", ["example.com"])

    assert not (tmp_path / "secrets.json").exists()


def test_hosts_can_be_changed_without_the_value_and_the_value_replaced(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)
    store.save("K", "value-one-1", ["a.example.com"])

    store.save("K", None, ["b.example.com", "*.c.example.com"])
    assert store.hosts_of("K") == ["b.example.com", "*.c.example.com"]
    assert store.resolve("K") == "value-one-1"

    store.save("K", "value-two-2", ["b.example.com"])
    assert store.resolve("K") == "value-two-2"


@pytest.mark.parametrize(
    ("name", "value", "hosts", "message"),
    [
        ("1bad", "value-ok-1", ["a.com"], "name"),
        ("has space", "value-ok-1", ["a.com"], "name"),
        ("OK", "", ["a.com"], "empty"),
        ("OK", "value-ok-1", [], "at least one host"),
        ("OK", "value-ok-1", ["https://a.com"], "isn't a host name"),
        ("OK", "value-ok-1", ["a.com/path"], "isn't a host name"),
        ("OK", "value-ok-1", ["a.com:443"], "isn't a host name"),
        ("OK", "value-ok-1", ["localhost"], "isn't a host name"),
        ("OK", "value-ok-1", "a.com", "list of host names"),
    ],
)
def test_what_the_store_refuses(
    name: str, value: str, hosts: object, message: str, tmp_path: Path, keychain: _FakeKeyring
) -> None:
    with pytest.raises(SecretError, match=message):
        SecretStore(tmp_path).save(name, value, hosts)

    assert keychain.store == {}


def test_a_value_too_short_to_tell_from_ordinary_text_is_refused(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    with pytest.raises(SecretError, match="at least 8"):
        SecretStore(tmp_path).save("PIN", "1234567", ["a.com"])

    assert keychain.store == {}


def test_a_new_secret_needs_a_value(tmp_path: Path, keychain: _FakeKeyring) -> None:
    with pytest.raises(SecretError, match="needs a value"):
        SecretStore(tmp_path).save("NEW", None, ["a.com"])


@pytest.mark.parametrize(
    ("pattern", "host", "allowed"),
    [
        ("api.example.com", "api.example.com", True),
        ("api.example.com", "API.example.com", True),
        ("api.example.com", "evil.example.com", False),
        ("api.example.com", "api.example.com.evil.net", False),
        ("*.example.com", "api.example.com", True),
        ("*.example.com", "a.b.example.com", True),
        ("*.example.com", "example.com", False),
        ("*.example.com", "badexample.com", False),
    ],
)
def test_host_matching(pattern: str, host: str, allowed: bool) -> None:
    assert host_allowed(pattern, host) is allowed


def test_a_secret_missing_from_the_keychain_is_a_clear_error_naming_it(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)
    store.save("GONE", "value-gone-1", ["a.com"])
    keychain.store.clear()

    with pytest.raises(SecretError, match="GONE"):
        store.resolve("GONE")
    with pytest.raises(SecretError, match="no secret named NOPE"):
        store.resolve("NOPE")


def test_deleting_a_secret_removes_its_keychain_entry_and_every_environments_use_of_it(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)
    store.save("A", "value-aaaa", ["a.com"])
    store.save("B", "value-bbbb", ["b.com"])
    in_environment(tmp_path, "s1", secrets=["A", "B"])
    in_environment(tmp_path, "s2", variables={"X": "1"}, secrets=["A"])
    environments = SessionEnvironments(tmp_path)

    assert store.delete("A") is True

    assert store.names() == {"B"}
    assert ("coscribe", "secret:A") not in keychain.store
    assert environments.get("s1")["secrets"] == ["B"]
    assert environments.get("s2") == {"variables": {"X": "1"}, "secrets": []}
    assert store.delete("A") is False


# -- what the store says when it refuses --


def _refusal(call: object) -> str:
    with pytest.raises(SecretError) as raised:
        call()  # type: ignore[operator]
    return str(raised.value)


def test_the_messages_for_a_bad_host_list_say_what_to_give(tmp_path: Path) -> None:
    store = SecretStore(tmp_path)

    assert _refusal(lambda: store.save("K", "value-ok-1", "a.com")) == (
        "hosts must be a list of host names."
    )
    assert _refusal(lambda: store.save("K", "value-ok-1", ["HTTPS://a.com "])) == (
        "'https://a.com' isn't a host name: give just the host, like api.example.com "
        "or *.example.com, with no https:// or path."
    )
    assert _refusal(lambda: store.save("K", "value-ok-1", [])) == (
        "A secret needs at least one host it may be sent to."
    )


def test_a_host_must_be_plain_ascii_so_the_secrets_file_stays_ascii(tmp_path: Path) -> None:
    store = SecretStore(tmp_path)

    assert "isn't a host name" in _refusal(lambda: store.save("K", "value-ok-1", ["例え.jp"]))
    assert "isn't a host name" in _refusal(lambda: store.save("K", "value-ok-1", ["bücher.de"]))


def test_a_secret_may_have_twenty_hosts_but_not_twenty_one(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)
    hosts = [f"h{i}.example.com" for i in range(21)]

    assert store.save("K", "value-ok-1", hosts[:20])["hosts"] == hosts[:20]
    assert _refusal(lambda: store.save("K", "value-ok-1", hosts)) == (
        "At most 20 hosts per secret."
    )


def test_what_save_says_about_a_bad_name_or_value(tmp_path: Path, keychain: _FakeKeyring) -> None:
    store = SecretStore(tmp_path)

    assert _refusal(lambda: store.save("1bad", "value-ok-1", ["a.com"])) == (
        "A secret's name is letters, digits and underscores, not starting with a digit."
    )
    assert _refusal(lambda: store.save("NEW", None, ["a.com"])) == "A new secret needs a value."
    assert _refusal(lambda: store.save("K", "", ["a.com"])) == "The value can't be empty."
    assert _refusal(lambda: store.save("K", "short", ["a.com"])) == (
        "A value is at least 8 characters: a shorter one can't be told "
        "from ordinary text, so it could not be kept out of what the model reads."
    )
    assert _refusal(lambda: store.save("K", "v" * 16385, ["a.com"])) == (
        "A value is at most 16384 characters."
    )
    assert keychain.store == {}


def test_a_value_of_the_longest_allowed_length_is_kept(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    SecretStore(tmp_path).save("K", "v" * 16384, ["a.com"])

    assert keychain.store[("coscribe", "secret:K")] == "v" * 16384


def test_what_save_says_when_the_keychain_cannot_keep_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = SecretStore(tmp_path)
    monkeypatch.setattr(secrets, "keychain_backend_usable", lambda: False)

    assert _refusal(lambda: store.save("K", "value-ok-1", ["a.com"])) == (
        "This computer has no keychain to keep a secret in, and secrets are "
        "never written to a plain file. On Windows that is Credential Manager; "
        "on Linux it needs a Secret Service such as GNOME Keyring."
    )

    monkeypatch.setattr(secrets, "keychain_backend_usable", lambda: True)
    monkeypatch.setattr(secrets, "store_secret", lambda ref, value: value)

    with pytest.raises(KeychainUnavailable) as raised:
        store.save("K", "value-ok-1", ["a.com"])
    assert str(raised.value) == "The keychain refused to store this secret."


def test_what_resolve_says_when_a_secret_cannot_be_read(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)
    store.save("GONE", "value-gone-1", ["a.com"])
    keychain.store.clear()

    message = _refusal(lambda: store.resolve("GONE"))
    assert message.startswith("The secret GONE can't be read from the keychain (")
    assert message.endswith("). Enter it again in Settings > Secrets.")

    (tmp_path / "secrets.json").write_text(json.dumps({"EMPTY": {"hosts": ["a.com"]}}))
    assert _refusal(lambda: store.resolve("EMPTY")) == (
        "The secret EMPTY has no value. Enter it again in Settings."
    )


# -- what is kept, and how --


def test_save_keeps_the_first_creation_time_and_returns_what_it_wrote(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)

    first = store.save("K", "value-one-1", ["a.com"])
    created = datetime.fromisoformat(first["created_at"])
    assert created.utcoffset() == UTC.utcoffset(None)
    assert abs((datetime.now(UTC) - created).total_seconds()) < 60
    assert first == {"name": "K", "hosts": ["a.com"], "created_at": first["created_at"]}

    assert store.save("K", "value-two-2", ["b.com"]) == {
        "name": "K",
        "hosts": ["b.com"],
        "created_at": first["created_at"],
    }
    assert store.save("K", None, ["c.com"])["created_at"] == first["created_at"]


def test_the_file_holds_a_readable_record_without_the_value(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path / "state" / "nested")

    saved = store.save("K", "value-one-1", ["a.com"])

    on_disk = (tmp_path / "state" / "nested" / "secrets.json").read_text()
    entry = {
        "ref": {"keyring_ref": "secret:K"},
        "hosts": ["a.com"],
        "created_at": saved["created_at"],
    }
    assert on_disk == json.dumps({"K": entry}, indent=2)
    assert not list((tmp_path / "state" / "nested").glob("*.tmp"))


def test_entries_list_names_hosts_and_creation_time_only(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)
    created = store.save("B", "value-bbbb", ["b.com"])["created_at"]
    (tmp_path / "secrets.json").write_text(
        json.dumps(
            {
                "B": {
                    "ref": {"keyring_ref": "secret:B"},
                    "hosts": ["b.com"],
                    "created_at": created,
                },
                "A": {"ref": {"keyring_ref": "secret:A"}},
            }
        )
    )

    assert store.entries() == [
        {"name": "A", "hosts": [], "created_at": None},
        {"name": "B", "hosts": ["b.com"], "created_at": created},
    ]


def test_hosts_of_an_unknown_secret_is_none_and_of_a_bare_entry_is_empty(tmp_path: Path) -> None:
    (tmp_path / "secrets.json").write_text(json.dumps({"BARE": {"ref": "x"}}))
    store = SecretStore(tmp_path)

    assert store.hosts_of("MISSING") is None
    assert store.hosts_of("BARE") == []


def test_a_secrets_file_that_is_not_a_map_counts_as_empty(tmp_path: Path) -> None:
    (tmp_path / "secrets.json").write_text(json.dumps(["not", "a", "map"]))

    store = SecretStore(tmp_path)

    assert store.names() == set()
    assert store.entries() == []


def test_saving_and_deleting_drop_the_redaction_cache_for_that_file(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    store = SecretStore(tmp_path)
    store.save("K", "value-one-1", ["a.com"])
    store_module.redactor(tmp_path)("text")
    assert str(store.path) in store_module._FORMS_CACHE

    store.save("K", "value-two-2", ["a.com"])
    assert str(store.path) not in store_module._FORMS_CACHE

    store_module.redactor(tmp_path)("text")
    store.delete("K")
    assert str(store.path) not in store_module._FORMS_CACHE


def _record_text_encodings(monkeypatch: pytest.MonkeyPatch) -> list[str | None]:
    seen: list[str | None] = []
    real_read, real_write = Path.read_text, Path.write_text

    def read_text(self: Path, encoding: str | None = None, errors: str | None = None) -> str:
        seen.append(encoding)
        return real_read(self, encoding=encoding, errors=errors)

    def write_text(
        self: Path, data: str, encoding: str | None = None, errors: str | None = None
    ) -> int:
        seen.append(encoding)
        return real_write(self, data, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(Path, "write_text", write_text)
    return seen


def test_the_store_files_are_read_and_written_as_utf8_whatever_the_locale(
    tmp_path: Path, keychain: _FakeKeyring, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _record_text_encodings(monkeypatch)
    store = SecretStore(tmp_path)

    store.save("K", "value-one-1", ["a.com"])
    store.names()
    in_environment(tmp_path, "t", variables={"LABEL": "名称"}, secrets=["K"])
    SessionEnvironments(tmp_path).get("t")
    store.delete("K")

    assert seen
    assert all(e is not None and codecs.lookup(e).name == "utf-8" for e in seen), seen


# -- placeholders --


def test_placeholders_are_found_and_replaced_by_name() -> None:
    text = "curl -H 'Authorization: {{secret:API_KEY}}' {{secret:B_1}} {{secret:API_KEY}} {{x}}"

    assert store_module.placeholders_in(text) == {"API_KEY", "B_1"}
    assert store_module.substitute(text, {"API_KEY": "k1", "B_1": "b1"}) == (
        "curl -H 'Authorization: k1' b1 k1 {{x}}"
    )
    assert store_module.placeholders_in("no placeholders here") == set()


# -- redaction --


def _store_with(tmp_path: Path, keychain: _FakeKeyring, **values: str) -> Path:
    store = SecretStore(tmp_path)
    for name, value in values.items():
        store.save(name, value, ["a.com"])
    return tmp_path


def test_a_value_is_redacted_in_every_common_encoding(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    value = 'pa"ss\\word\n-1'
    redact = store_module.redactor(_store_with(tmp_path, keychain, K=value))
    raw = value.encode("utf-8")
    forms = [
        value,
        store_module.quote(value, safe=""),
        raw.hex(),
        raw.hex().upper(),
        json.dumps(value)[1:-1],
        base64.b64encode(raw).decode("ascii"),
        base64.urlsafe_b64encode(raw).decode("ascii"),
        base64.b64encode(raw).decode("ascii").rstrip("="),
    ]

    for form in forms:
        assert redact(f"before {form} after") == "before [REDACTED SECRET] after", form
    assert redact("") == ""
    assert redact("nothing to hide") == "nothing to hide"


def test_the_redaction_forms_do_not_swallow_a_look_alike_ending_in_x(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    value = "abcdefghW"
    encoded = base64.b64encode(value.encode()).decode()
    assert encoded.endswith("X") and "=" not in encoded
    redact = store_module.redactor(_store_with(tmp_path, keychain, K=value))

    assert redact(f"see {encoded[:-1]} here") == f"see {encoded[:-1]} here"
    assert redact(f"see {encoded} here") == "see [REDACTED SECRET] here"


def test_the_longer_of_two_overlapping_values_is_redacted_whole(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    redact = store_module.redactor(
        _store_with(tmp_path, keychain, A_SHORT="bcdefghi", B_LONG="abcdefghi")
    )

    assert redact("x abcdefghi y") == "x [REDACTED SECRET] y"


def test_the_redaction_forms_are_cached_until_the_file_changes(
    tmp_path: Path, keychain: _FakeKeyring
) -> None:
    redact = store_module.redactor(_store_with(tmp_path, keychain, K="value-one-1"))

    redact("a")
    reads = keychain.reads
    redact("b")
    redact("c")
    assert keychain.reads == reads

    # A second secret written behind the store's back: only the file's own stamp tells.
    # The size differs too, and the mtime is moved on explicitly so a coarse clock cannot hide it.
    keychain.store[("coscribe", "secret:J")] = "value-two-2"
    secrets_file = tmp_path / "secrets.json"
    before = secrets_file.stat().st_mtime_ns
    secrets_file.write_text(
        json.dumps(
            {
                "K": {"ref": {"keyring_ref": "secret:K"}, "hosts": ["a.com"]},
                "J": {"ref": {"keyring_ref": "secret:J"}, "hosts": ["a.com"]},
            }
        )
    )
    os.utime(secrets_file, ns=(before + 1_000_000_000, before + 1_000_000_000))
    assert redact("x value-two-2 y") == "x [REDACTED SECRET] y"


def test_one_unreadable_secret_does_not_stop_the_others_being_redacted(
    tmp_path: Path, keychain: _FakeKeyring, monkeypatch: pytest.MonkeyPatch
) -> None:
    _store_with(tmp_path, keychain, A_GOOD="value-good-1", Z_GOOD="value-good-2")
    store = SecretStore(tmp_path)
    data = json.loads(store.path.read_text())
    data["A_BAD"] = {"ref": {"keyring_ref": "secret:A_BAD"}, "hosts": ["a.com"]}
    store.path.write_text(json.dumps(data))
    keychain.unreadable.add("secret:A_BAD")
    monkeypatch.setattr(SecretStore, "names", lambda self: ["A_BAD", "A_GOOD", "Z_GOOD"])

    redact = store_module.redactor(tmp_path)

    assert redact("value-good-1 and value-good-2") == "[REDACTED SECRET] and [REDACTED SECRET]"


def test_redaction_with_no_secrets_file_changes_nothing(tmp_path: Path) -> None:
    assert store_module.redactor(tmp_path / "missing")("value-good-1") == "value-good-1"
