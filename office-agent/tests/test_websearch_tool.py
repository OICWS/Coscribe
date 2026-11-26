import threading
from collections.abc import Iterator
from typing import Any

import pytest

from coscribe.runtime import get_tool_metadata
from coscribe.tools.web import _search, websearch
from coscribe.tools.web.websearch import build_websearch_tools, web_search

# `ddgs.DDGS` is a lazy stand-in that dispatches to `ddgs.ddgs.DDGS`, so the real class is what
# the tests patch.


@pytest.fixture(autouse=True)
def _fresh_search_memory() -> Iterator[None]:
    _search.forget_unreachable()
    yield
    _search.forget_unreachable()


def test_web_search_normalizes_ddgs_result_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_text(self: Any, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        captured["query"] = query
        captured["kwargs"] = kwargs
        return [
            {
                "title": "Paris - Wikipedia",
                "href": "https://en.wikipedia.org/wiki/Paris",
                "body": "Paris is the capital of France.",
            },
            {"title": "Another result", "href": "https://example.com", "body": "some snippet"},
        ]

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", _fake_text)

    results = web_search("capital of France")

    assert captured["query"] == "capital of France"
    assert captured["kwargs"]["backend"] in _search.engine_names()
    assert captured["kwargs"]["max_results"] == 5
    assert results == [
        {
            "title": "Paris - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Paris",
            "snippet": "Paris is the capital of France.",
        },
        {"title": "Another result", "url": "https://example.com", "snippet": "some snippet"},
    ]


def test_web_search_respects_max_results(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_text(self: Any, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        captured["kwargs"] = kwargs
        return [{"title": "T", "href": "https://example.com", "body": "B"}]

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", _fake_text)

    web_search("anything", max_results=2)

    assert captured["kwargs"]["max_results"] == 2


def test_web_search_handles_missing_fields_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_text(self: Any, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        return [{}]  # a backend returning a sparse result shouldn't crash the tool

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", _fake_text)

    results = web_search("anything")

    assert results == [{"title": "", "url": "", "snippet": ""}]


def test_web_search_forwards_https_proxy_to_ddgs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_init(self: Any, proxy: str | None = None, **kwargs: Any) -> None:
        captured["proxy"] = proxy

    def _fake_text(self: Any, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"title": "T", "href": "https://example.com", "body": "B"}]

    monkeypatch.setattr("ddgs.ddgs.DDGS.__init__", _fake_init)
    monkeypatch.setattr("ddgs.ddgs.DDGS.text", _fake_text)
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:8080")

    web_search("anything")

    assert captured["proxy"] == "http://proxy.example.com:8080"


def test_web_search_passes_no_proxy_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_init(self: Any, proxy: str | None = None, **kwargs: Any) -> None:
        captured["proxy"] = proxy

    def _fake_text(self: Any, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"title": "T", "href": "https://example.com", "body": "B"}]

    monkeypatch.setattr("ddgs.ddgs.DDGS.__init__", _fake_init)
    monkeypatch.setattr("ddgs.ddgs.DDGS.text", _fake_text)
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(var, raising=False)

    web_search("anything")

    assert captured["proxy"] is None


def test_web_search_tool_metadata() -> None:
    tools = build_websearch_tools()
    assert [t.__name__ for t in tools] == ["web_search", "read_web_page"]
    for tool in tools:
        metadata = get_tool_metadata(tool)
        assert metadata.risk_category == "READ"
        assert metadata.category == "web"
        assert metadata.requires_approval is False


def _serve(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    import httpx

    real_client = httpx.Client

    def client(**kwargs: Any) -> Any:
        kwargs.pop("proxy", None)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(websearch.httpx, "Client", client)


def test_read_web_page_returns_the_main_text_as_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from coscribe.tools.web.websearch import read_web_page

    html = (
        "<html><head><title>Q3 results</title><script>track()</script></head><body>"
        "<nav>Home | About</nav><main><h1>Q3 results</h1><p>Revenue grew <b>12%</b>.</p>"
        "</main><footer>(c) 2026</footer></body></html>"
    )
    _serve(monkeypatch, lambda request: httpx.Response(200, html=html))

    page = read_web_page("https://example.com/q3", max_chars=20)

    assert page["title"] == "Q3 results"
    assert page["content"] == "# Q3 results\n\nRevenu"
    assert page["next_start"] == 20
    rest = read_web_page("https://example.com/q3", start=20)
    assert rest["content"] == "e grew **12%**." and rest["next_start"] is None
    assert "Home" not in rest["content"] and "track" not in rest["content"]


def test_read_web_page_refuses_what_isnt_a_page(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from coscribe.tools.web.websearch import read_web_page

    _serve(
        monkeypatch,
        lambda request: httpx.Response(
            200, content=b"%PDF", headers={"content-type": "application/pdf"}
        ),
    )
    with pytest.raises(ValueError, match="is application/pdf, not a page to read"):
        read_web_page("https://example.com/report.pdf")
    with pytest.raises(ValueError, match="isn't an http"):
        read_web_page("file:///etc/passwd")


def test_web_search_asks_each_engine_on_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    backends: list[str] = []
    lock = threading.Lock()

    def _fake_text(self: Any, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        with lock:
            backends.append(kwargs["backend"])
        return []

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", _fake_text)
    monkeypatch.setattr(websearch, "_SEARCH_RETRY_SECONDS", 0)

    with pytest.raises(_search.SearchEmptyError):
        web_search("anything")

    assert sorted(backends) == sorted(_search.engine_names() * 2)
    assert _search.engine_names()[-2:] == ["wikipedia", "grokipedia"]


def test_web_search_retries_a_query_the_engines_briefly_turned_away(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ddgs.exceptions import DDGSException

    rounds = {"brave": 0}

    def flaky_text(self: object, query: str, **kwargs: Any) -> list[dict[str, str]]:
        if kwargs["backend"] != "brave":
            raise DDGSException("No results found.")
        rounds["brave"] += 1
        if rounds["brave"] < 2:
            raise DDGSException("No results found.")
        return [{"title": "T", "href": "https://example.com", "body": "B"}]

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", flaky_text)
    monkeypatch.setattr(websearch, "_SEARCH_RETRY_SECONDS", 0)

    assert web_search("ai news") == [{"title": "T", "url": "https://example.com", "snippet": "B"}]
    assert rounds["brave"] == 2


def test_web_search_says_the_engines_answered_with_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ddgs.exceptions import DDGSException, TimeoutException

    def some_reached(self: object, query: str, **kwargs: Any) -> list[dict[str, str]]:
        if kwargs["backend"] == "mojeek":
            raise DDGSException("No results found.")
        raise TimeoutException("operation timed out")

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", some_reached)
    monkeypatch.setattr(websearch, "_SEARCH_RETRY_SECONDS", 0)

    with pytest.raises(_search.SearchEmptyError, match="1 search engine"):
        web_search("nothing")


def _unreachable_engines(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from ddgs.exceptions import DDGSException, TimeoutException

    calls: list[str] = []
    lock = threading.Lock()

    def fails(self: object, query: str, **kwargs: Any) -> list[dict[str, str]]:
        with lock:
            calls.append(kwargs["backend"])
        if kwargs["backend"] == "yahoo":
            raise DDGSException("RequestError: error sending request for url")
        raise TimeoutException("operation timed out")

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", fails)
    return calls


def test_web_search_says_no_engine_could_be_reached_and_remembers_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _unreachable_engines(monkeypatch)
    for var in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(websearch, "configured_proxy", lambda url=None: None)

    with pytest.raises(_search.SearchUnreachableError, match="from this network") as first:
        web_search("anything")
    assert "Settings > General > Proxy" in str(first.value)
    assert len(calls) == len(_search.engine_names())  # not retried

    with pytest.raises(_search.SearchUnreachableError):
        web_search("other words")
    assert len(calls) == len(_search.engine_names())  # answered from memory


def test_web_search_names_a_proxy_that_reaches_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _unreachable_engines(monkeypatch)
    monkeypatch.setattr(
        websearch, "configured_proxy", lambda url=None: "http://user:secret@127.0.0.1:10808"
    )

    with pytest.raises(_search.SearchUnreachableError, match="through the proxy") as raised:
        web_search("anything")
    assert "http://127.0.0.1:10808" in str(raised.value)
    assert "secret" not in str(raised.value)

    # A different proxy is a different network: it is asked, not answered from memory.
    monkeypatch.setattr(websearch, "configured_proxy", lambda url=None: "http://127.0.0.1:7890")
    with pytest.raises(_search.SearchUnreachableError):
        web_search("anything")
    assert len(calls) == 2 * len(_search.engine_names())


def test_web_search_does_not_wait_for_an_engine_that_hangs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = threading.Event()

    def text(self: object, query: str, **kwargs: Any) -> list[dict[str, str]]:
        if kwargs["backend"] == "brave":
            return [{"title": "T", "href": "https://example.com", "body": "B"}]
        release.wait(10)
        return []

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", text)
    monkeypatch.setattr(_search, "GRACE_SECONDS", 0.05)
    try:
        assert web_search("anything") == [
            {"title": "T", "url": "https://example.com", "snippet": "B"}
        ]
        assert not release.is_set()
    finally:
        release.set()


def test_web_search_gives_up_at_its_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    release = threading.Event()

    def hangs(self: object, query: str, **kwargs: Any) -> list[dict[str, str]]:
        release.wait(10)
        return []

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", hangs)
    monkeypatch.setattr(_search, "DEADLINE_SECONDS", 0.05)
    try:
        with pytest.raises(_search.SearchUnreachableError):
            web_search("anything")
    finally:
        release.set()


def test_read_web_page_says_why_it_could_not_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from coscribe.tools.web.websearch import read_web_page

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("handshake operation timed out", request=request)

    _serve(monkeypatch, refuse)
    monkeypatch.setattr(websearch, "configured_proxy", lambda url=None: None)
    with pytest.raises(ConnectionError, match="connect to example.com: the connection timed out"):
        read_web_page("https://example.com/a")

    monkeypatch.setattr(
        websearch, "configured_proxy", lambda url=None: "http://u:p@127.0.0.1:10808"
    )
    with pytest.raises(ConnectionError, match=r"through the proxy http://127\.0\.0\.1:10808"):
        read_web_page("https://example.com/a")


_DEEPSEEK = {"ds": {"base_url": "https://api.deepseek.com/v1", "api_key": "sk-test"}}


def _deepseek(monkeypatch: pytest.MonkeyPatch, handler: Any, site: Any = None) -> list[Any]:
    """DeepSeek's API answered by `handler`, any other host by `site`; the requests to DeepSeek."""
    import httpx

    seen: list[Any] = []
    real_client = httpx.Client

    def route(request: httpx.Request) -> httpx.Response:
        if request.url.host != "api.deepseek.com":
            response: httpx.Response = site(request)
            return response
        seen.append(request)
        response = handler(request)
        return response

    def client(**kwargs: Any) -> Any:
        kwargs.pop("proxy", None)
        return real_client(transport=httpx.MockTransport(route), **kwargs)

    monkeypatch.setattr(httpx, "Client", client)
    return seen


def _engines_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    from ddgs.exceptions import TimeoutException

    def blocked(self: object, query: str, **kwargs: Any) -> list[dict[str, str]]:
        raise TimeoutException("operation timed out")

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", blocked)
    monkeypatch.setattr(websearch, "configured_proxy", lambda url=None: None)


def _search_tool(providers: dict[str, dict[str, str]]) -> Any:
    return build_websearch_tools(None, lambda: providers)[0]


def test_web_search_falls_back_to_the_providers_own_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    _engines_blocked(monkeypatch)
    seen = _deepseek(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json={
                "results": [
                    {"title": "Timeouts", "url": "https://www.python-httpx.org/", "snippet": "S"}
                ]
            },
        ),
    )

    found = _search_tool(_DEEPSEEK)("httpx " + "timeout " * 30, max_results=3)

    assert found == [{"title": "Timeouts", "url": "https://www.python-httpx.org/", "snippet": "S"}]
    request = seen[0]
    assert str(request.url) == "https://api.deepseek.com/v1/tools/search"
    assert request.headers["authorization"] == "Bearer sk-test"
    body = __import__("json").loads(request.content)
    assert body["count"] == 3 and len(body["query"]) == 128


def test_web_search_uses_the_free_engines_first(monkeypatch: pytest.MonkeyPatch) -> None:
    def text(self: object, query: str, **kwargs: Any) -> list[dict[str, str]]:
        return [{"title": "T", "href": "https://example.com", "body": "B"}]

    monkeypatch.setattr("ddgs.ddgs.DDGS.text", text)
    seen = _deepseek(monkeypatch, lambda request: pytest.fail("the provider was asked"))

    assert _search_tool(_DEEPSEEK)("anything")[0]["url"] == "https://example.com"
    assert seen == []


def test_web_search_says_both_ways_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    _engines_blocked(monkeypatch)
    answers = [
        httpx.Response(402, json={"error": {"message": "Insufficient Balance"}}),
        httpx.Response(200, json={"results": []}),
    ]
    _deepseek(monkeypatch, lambda request: answers.pop(0))

    with pytest.raises(_search.SearchUnreachableError, match="no balance left") as raised:
        _search_tool(_DEEPSEEK)("anything")
    assert "from this network" in str(raised.value) and "sk-test" not in str(raised.value)

    with pytest.raises(_search.SearchUnreachableError, match="DeepSeek found nothing either"):
        _search_tool(_DEEPSEEK)("anything")


def test_web_search_without_a_search_provider_uses_only_the_free_engines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _engines_blocked(monkeypatch)
    seen = _deepseek(monkeypatch, lambda request: pytest.fail("a provider was asked"))
    others = {"kimi": {"base_url": "https://api.moonshot.ai/v1", "api_key": "sk"}}

    with pytest.raises(_search.SearchUnreachableError):
        _search_tool(others)("anything")
    assert seen == []


def test_read_web_page_reads_through_the_provider_when_the_site_cant_be_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection reset", request=request)

    monkeypatch.setattr(websearch, "configured_proxy", lambda url=None: None)
    seen = _deepseek(
        monkeypatch,
        lambda request: httpx.Response(200, json={"title": "Page", "content": "# Hello\n\nWorld"}),
        refuse,
    )
    read = build_websearch_tools(None, lambda: _DEEPSEEK)[1]

    page = read("https://example.com/a", max_chars=7)

    assert page == {
        "url": "https://example.com/a",
        "title": "Page",
        "content": "# Hello",
        "total_chars": 14,
        "next_start": 7,
    }
    assert str(seen[0].url) == "https://api.deepseek.com/v1/tools/fetch"


def test_read_web_page_keeps_a_limited_conversation_off_the_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    import httpx

    from coscribe.runtime import NetworkGuard

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection reset", request=request)

    monkeypatch.setattr(websearch, "configured_proxy", lambda url=None: None)
    seen = _deepseek(monkeypatch, lambda request: pytest.fail("the provider was asked"), refuse)
    network = NetworkGuard(tmp_path, "t1")
    monkeypatch.setattr(network, "sites", lambda: ["example.com"])
    read = build_websearch_tools(network, lambda: _DEEPSEEK)[1]

    with pytest.raises(ConnectionError, match="connect to example.com"):
        read("https://example.com/a")
    assert seen == []
