"""Property tests for the promise in docs/decisions/0003-secrets-promise.md:
a stored secret's value, in each form `redactor` claims to cover, never
survives in a text, wherever it sits. Example tests pick a few positions;
these let Hypothesis pick them.

The forms are listed here again, from the `_forms` docstring, instead of read
back from the code: a form dropped from the code must make a test fail.
"""

from __future__ import annotations

import base64
import json
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import keyring.errors
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from coscribe.runtime import secrets
from coscribe.runtime.secret_store import MAX_VALUE, MIN_VALUE, SecretStore, redactor
from coscribe.runtime_lg.audit import redact_secrets

_SETTINGS = settings(deadline=None, derandomize=True, max_examples=100)

_MARK = "[REDACTED SECRET]"


class _FakeKeyring:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}
        self.errors = keyring.errors

    def set_password(self, service: str, ref: str, value: str) -> None:
        self.store[(service, ref)] = value

    def get_password(self, service: str, ref: str) -> str | None:
        return self.store.get((service, ref))

    def delete_password(self, service: str, ref: str) -> None:
        self.store.pop((service, ref), None)


@contextmanager
def _redactor_for(values: list[str]) -> Iterator[Callable[[str], str]]:
    """A redactor over a fresh state folder holding `values` as secrets. The
    folder and keychain are made per example: a function-scoped fixture would
    be shared by all of them."""
    with pytest.MonkeyPatch.context() as patch, tempfile.TemporaryDirectory() as folder:
        patch.setattr(secrets, "keyring", _FakeKeyring())
        patch.setattr(secrets, "keychain_backend_usable", lambda: True)
        store = SecretStore(folder)
        for index, value in enumerate(values):
            store.save(f"SECRET_{index}", value, ["example.com"])
        yield redactor(Path(folder))


def _forms(value: str) -> set[str]:
    raw = value.encode("utf-8")
    forms = {value, quote(value, safe=""), quote(value), raw.hex(), raw.hex().upper()}
    forms.add(json.dumps(value)[1:-1])
    for encoder in (base64.b64encode, base64.urlsafe_b64encode):
        encoded = encoder(raw).decode("ascii")
        forms.update({encoded, encoded.rstrip("=")})
    return {form for form in forms if len(form) >= MIN_VALUE}


# Surrogates cannot be encoded to UTF-8, so no keychain or HTTP body holds one.
_TEXT = st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=40)
_VALUES = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)), min_size=MIN_VALUE, max_size=60
)
# Text a form could not be a piece of by accident, so that "unchanged" and
# "gone" mean what they say.
_PROSE_ALPHABET = "abcdefghij .,\n"
_PROSE = st.text(alphabet=_PROSE_ALPHABET, max_size=40)


def _assume_mark_free(value: str) -> None:
    # A value that spells the replacement mark would "survive" as the mark.
    assume(not any(_MARK in form or form in _MARK for form in _forms(value)))


@_SETTINGS
@given(value=_VALUES, before=_TEXT, after=_TEXT, data=st.data())
def test_every_covered_form_is_gone_wherever_it_sits(
    value: str, before: str, after: str, data: st.DataObject
) -> None:
    _assume_mark_free(value)
    form = data.draw(st.sampled_from(sorted(_forms(value))))
    with _redactor_for([value]) as redact:
        for text in (form, form + after, before + form, before + form + after):
            out = redact(text)
            assert form not in out, f"{form!r} survived in {out!r}"


@_SETTINGS
@given(value=_VALUES, gaps=st.lists(_TEXT, min_size=2, max_size=5), data=st.data())
def test_a_form_repeated_is_gone_every_time(
    value: str, gaps: list[str], data: st.DataObject
) -> None:
    _assume_mark_free(value)
    forms = sorted(_forms(value))
    picked = [data.draw(st.sampled_from(forms)) for _ in gaps]
    text = "".join(gap + form for gap, form in zip(gaps, picked, strict=True))
    with _redactor_for([value]) as redact:
        out = redact(text)
    assert all(form not in out for form in picked), out


@_SETTINGS
@given(values=st.lists(_VALUES, min_size=2, max_size=4, unique=True), gaps=_TEXT)
def test_secrets_side_by_side_are_all_gone(values: list[str], gaps: str) -> None:
    for value in values:
        _assume_mark_free(value)
    # A form of one secret that is a piece of another's would be replaced
    # first, and the shorter one then reads differently: not a leak of either.
    all_forms = [_forms(value) for value in values]
    for i, mine in enumerate(all_forms):
        for j, theirs in enumerate(all_forms):
            assume(i == j or not any(a in b for a in mine for b in theirs))
    text = gaps.join(sorted(_forms(value))[0] for value in values)
    with _redactor_for(values) as redact:
        out = redact(text)
    for forms in all_forms:
        assert not any(form in out for form in forms), out


@_SETTINGS
@given(value=_VALUES, text=_PROSE)
def test_a_text_with_no_secret_comes_back_unchanged(value: str, text: str) -> None:
    assume(not any(form in text for form in _forms(value)))
    with _redactor_for([value]) as redact:
        assert redact(text) == text


@_SETTINGS
@given(text=_TEXT)
def test_with_no_secret_stored_nothing_is_changed(text: str) -> None:
    with _redactor_for([]) as redact:
        assert redact(text) == text


def test_the_longest_allowed_value_is_still_covered() -> None:
    value = "k" * MAX_VALUE
    with _redactor_for([value]) as redact:
        assert redact("x" + value + "y") == f"x{_MARK}y"


# redact_secrets: "Recursively redact secret-shaped content from a JSON-like
# value" -- a secret-named key blanks its whole value; a known token format is
# blanked inside any string; nothing else changes and the shape is kept.
_KEY_NAMES = ["api_key", "Authorization", "client-secret", "password", "access_token"]
_TOKENS = st.one_of(
    st.from_regex(r"sk-ant-[A-Za-z0-9_-]{20,40}", fullmatch=True),
    st.from_regex(r"sk-proj-[A-Za-z0-9_-]{20,40}", fullmatch=True),
    st.from_regex(r"gh[oprsu]_[A-Za-z0-9]{20,40}", fullmatch=True),
    st.from_regex(r"github_pat_[A-Za-z0-9_]{20,40}", fullmatch=True),
    st.from_regex(r"xox[baprs]-[A-Za-z0-9-]{10,30}", fullmatch=True),
    st.from_regex(r"AIza[A-Za-z0-9_-]{30,40}", fullmatch=True),
    st.from_regex(r"AKIA[A-Z0-9]{16}", fullmatch=True),
    st.from_regex(r"glpat-[A-Za-z0-9_-]{15,30}", fullmatch=True),
)
_PLAIN_KEYS = st.text(alphabet="abdfghijlmnoruvwxyz", min_size=1, max_size=8)


def _json_like(
    leaf: st.SearchStrategy[object], *, secret_keys: bool = True
) -> st.SearchStrategy[object]:
    keys = st.one_of(_PLAIN_KEYS, st.sampled_from(_KEY_NAMES)) if secret_keys else _PLAIN_KEYS
    return st.recursive(
        leaf,
        lambda inner: st.one_of(
            st.lists(inner, max_size=3), st.dictionaries(keys, inner, max_size=3)
        ),
        max_leaves=8,
    )


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


@_SETTINGS
@given(tree=_json_like(st.one_of(_TOKENS, _PROSE)), token=_TOKENS, pad=_PROSE)
def test_a_token_is_gone_at_any_depth(tree: object, token: str, pad: str) -> None:
    # The spaces end the token: its character classes include letters.
    out = redact_secrets({"outer": [tree, {"note": f"{pad} {token} {pad}"}]})
    assert token not in json.dumps(out)
    assert out["outer"][1]["note"] == f"{pad} [REDACTED] {pad}"


@_SETTINGS
@given(tree=_json_like(st.one_of(_TOKENS, _PROSE, st.integers(), st.none(), st.booleans())))
def test_no_known_token_survives_and_the_shape_is_kept(tree: object) -> None:
    out = redact_secrets(tree)

    def shape(value: object) -> object:
        if isinstance(value, dict):
            return {k: shape(v) for k, v in value.items()}
        if isinstance(value, list):
            return [shape(v) for v in value]
        return type(value)

    assert shape(out) == shape(tree)
    tokens = [s for s in _strings(tree) if not set(s) <= set(_PROSE_ALPHABET)]
    assert not set(tokens) & set(_strings(out))


@_SETTINGS
@given(
    name=st.sampled_from(_KEY_NAMES),
    prefix=st.text(alphabet="abc_", max_size=4),
    value=_PROSE,
    nested=st.booleans(),
)
def test_a_secret_named_key_blanks_its_whole_string_value(
    name: str, prefix: str, value: str, nested: bool
) -> None:
    body: object = [value, [value]] if nested else value
    out = redact_secrets({prefix + name: body})
    expected = ["[REDACTED]", ["[REDACTED]"]] if nested else "[REDACTED]"
    assert out == {prefix + name: expected}


@_SETTINGS
@given(
    tree=_json_like(st.one_of(_PROSE, st.integers(), st.none(), st.booleans()), secret_keys=False)
)
def test_content_with_no_secret_comes_back_equal(tree: object) -> None:
    assert redact_secrets(tree) == tree
