from collections.abc import Iterator

import pytest

from coscribe.tools import _office_com

# The flaky-test policy (tests/flaky_policy.py): the hooks and the quarantine fixture
# register by being names in this module.
from .flaky_policy import (  # noqa: F401
    _quarantine,
    pytest_collection_modifyitems,
    pytest_runtest_logreport,
    pytest_terminal_summary,
)


@pytest.fixture(autouse=True)
def _no_office_program(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test starts the Microsoft Office or WPS installed on a developer's machine: previews and
    the deck overflow check would open Word or PowerPoint for every file a test writes, slowly and
    differently from CI, which has none. A test of the COM path fakes what it needs on top.

    A test marked `real_libreoffice` gets LibreOffice standing in for the office program, so a
    preview or a conversion is checked end to end; it skips itself where LibreOffice is absent."""
    monkeypatch.setattr(_office_com, "_registered", lambda prog_id: False)
    if request.node.get_closest_marker("real_libreoffice") is not None:
        from .libreoffice_probe import libreoffice_as_office

        monkeypatch.setattr(_office_com, "convert", libreoffice_as_office)


@pytest.fixture(autouse=True)
def _testserver_is_a_local_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Starlette's TestClient sends `Host: testserver`; the Host guard (web/local_guard.py) would
    refuse every request of every web test. Its own tests clear this and name hosts explicitly."""
    monkeypatch.setenv("COSCRIBE_ALLOWED_HOSTS", "testserver")


@pytest.fixture(autouse=True)
def _manual_permission_mode_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most tests script the model's exact replies, and Auto mode (the
    shipped default) adds a reviewer call before each gated action. Tests
    of the default itself override this."""
    monkeypatch.setenv("COSCRIBE_DEFAULT_PERMISSION_MODE", "manual")


@pytest.fixture(autouse=True)
def _check_chat_websocket_payloads(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Every payload the server sends on a chat WebSocket must match
    conversation/wire.py, so a test run is also a conformance run. The browser
    panel's socket speaks its own protocol and is left alone."""
    from starlette.websockets import WebSocket

    from .wire_check import check_event, violations

    violations.clear()
    original = WebSocket.send_json

    async def checked(self: WebSocket, data: object, mode: str = "text") -> None:
        if self.url.path != "/ws/browser":
            check_event(data)
        await original(self, data, mode)

    monkeypatch.setattr(WebSocket, "send_json", checked)
    yield
    assert not violations, violations
