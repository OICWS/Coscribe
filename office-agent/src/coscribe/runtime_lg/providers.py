"""Resolve provider and model IDs to their LangChain chat adapters."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr


def resolve_chat_model(
    model: str, custom_providers: dict[str, dict[str, str]] | None = None
) -> Any:
    """Return a LangChain BaseChatModel for a "provider:model" string.

    Custom connections use the settings returned by load_custom_providers.
    """
    if ":" not in model:
        raise ValueError(f'model must be a "provider:model" string, got {model!r}')
    provider_key, model_name = model.split(":", 1)
    custom_providers = custom_providers or {}

    if provider_key in custom_providers:
        return _custom_chat_model(model_name, custom_providers[provider_key])
    if provider_key == "anthropic":
        from langchain_anthropic import ChatAnthropic

        # ChatAnthropic's pydantic field is `model` aliased to `model_name` --
        # only the alias is accepted as a constructor kwarg (confirmed via
        # ChatAnthropic.model_fields; mypy rejects `model=` here). timeout/stop
        # are genuinely optional at runtime (pydantic fields with None
        # defaults) but mypy's generated __init__ stub treats them as
        # required without the pydantic mypy plugin configured -- passing
        # None explicitly is the accurate, not-a-workaround value anyway.
        return ChatAnthropic(model_name=model_name, timeout=None, stop=None)
    if provider_key == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        # NOT forcing transport="rest" anymore -- see git history for
        # why that was tried and reverted. Short version: it was based
        # on an incomplete diagnosis (assumed gRPC doesn't respect
        # HTTP_PROXY/HTTPS_PROXY reliably), which turned out to be
        # wrong -- gRPC's own docs confirm native support for
        # authenticated CONNECT proxies via these exact env vars
        # (RFC7617 Basic auth, username:password embedded in the URL,
        # same format this project's own .env convention already uses).
        # The real bug behind the original corporate-proxy hang was
        # `.env` not overriding an already-set OS environment variable
        # (python-dotenv's own override=False default -- see cli.py's
        # _load_settings), fixed separately. Forcing transport="rest"
        # instead traded that for a real bug in this SDK version's own
        # REST-async streaming path -- live-hit: "TypeError: object
        # ResponseIterator can't be used in 'await' expression" --
        # `langchain_google_genai`'s own retry-wrapping helper awaits
        # the return value of a streaming call as if it were a plain
        # coroutine, when a streaming REST call actually returns an
        # async-iterable object directly. That's an unusual, lightly-
        # exercised combination (most users hit either plain gRPC or a
        # genuinely custom Vertex endpoint, not "force REST against the
        # real default Gemini Developer API endpoint"). Reverting to
        # the plain default lets async calls use grpc_asyncio again,
        # the library's own best-tested path, now that the actual root
        # cause (.env not applying) is fixed at the source.
        #
        # max_retries=2, not the library's own default of 6: a live,
        # user-reported bug, root-caused by reading
        # langchain_google_genai's own retry decorator (chat_models.py,
        # _create_retry_decorator) -- it retries ResourceExhausted (a
        # quota error) with the same exponential backoff as a genuinely
        # transient one, up to ~60s of total waiting across 6 attempts.
        # A daily-quota-exhausted account will not recover within that
        # window no matter how many times it's retried, so those 6
        # attempts are pure dead time -- and during all of it, nothing
        # in this app can interrupt the call (session.py's stop flag is
        # only checked between already-yielded stream chunks, none of
        # which exist while stuck inside this retry loop), so the user
        # sees a spinner that won't stop and a model switch that
        # silently has no effect on the stuck turn. Two attempts keeps
        # a little real benefit for an actually-transient 429/503
        # (~1-2s of backoff) while capping the worst case at a few
        # seconds instead of over a minute. Previously observed and
        # documented (not fixed) in this exact shape -- see this
        # package's own README.md, "burning through most of a run's
        # remaining budget on one 429 before the process gave up."
        return ChatGoogleGenerativeAI(model=model_name, max_retries=2)
    if provider_key == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name)

    raise ValueError(f"Unsupported provider {provider_key!r}.")


def _custom_chat_model(model_name: str, config: dict[str, str]) -> Any:
    from langchain_openai import ChatOpenAI

    api_format = config.get("api_format")
    if api_format == "azure":
        from langchain_openai import AzureChatOpenAI
        from openai import DefaultAsyncHttpxClient, DefaultHttpxClient

        return AzureChatOpenAI(
            azure_endpoint=config["base_url"],
            azure_deployment=model_name,
            model=model_name,
            api_version=config["api_version"],
            api_key=SecretStr(config["api_key"]),
            azure_ad_token=None,
            base_url=None,
            use_responses_api=False,
            # Passing http clients turns off LangChain's automatic streamed usage for Azure.
            stream_usage=True,
            # A redirect could forward Azure's custom API-key header to a different host.
            http_client=DefaultHttpxClient(follow_redirects=False),
            http_async_client=DefaultAsyncHttpxClient(follow_redirects=False),
        )
    if api_format == "responses":
        return ChatOpenAI(
            model=model_name,
            base_url=config["base_url"],
            api_key=SecretStr(config["api_key"]),
            use_responses_api=True,
            store=False,
        )
    model_class = _deepseek_chat_model_class() if _is_deepseek(config["base_url"]) else ChatOpenAI
    return model_class(
        model=model_name,
        base_url=config["base_url"],
        api_key=SecretStr(config["api_key"]),
        # ChatOpenAI only auto-enables streamed usage_metadata when
        # base_url is unset (the real OpenAI endpoint) -- confirmed by
        # reading langchain_openai's own __init__ (its auto-enable
        # condition checks base_url is None). Any custom
        # OpenAI-compatible provider (DeepSeek, Kimi, GLM, ...) always
        # sets base_url, so without this explicit flag the usage bar
        # (conversation/session.py's _stream_turn) would silently never populate
        # for these providers specifically, unlike gemini:/anthropic:/
        # openai: -- see runtime_lg/README.md's "usage bar" section.
        stream_usage=True,
        use_responses_api=False if api_format == "chat_completions" else None,
    )


def with_prompt_cache_key(model: Any, key: str) -> Any:
    """OpenAI routes requests that share a prompt_cache_key to the same
    cache, so one key per conversation keeps its growing prefix warm
    (Codex sends its session id the same way). Only OpenAI's own endpoint:
    an OpenAI-compatible provider may reject a parameter it doesn't know."""
    from langchain_openai import ChatOpenAI

    if not isinstance(model, ChatOpenAI) or model.openai_api_base is not None:
        return model
    return model.model_copy(
        update={"model_kwargs": {**model.model_kwargs, "prompt_cache_key": key}}
    )


def for_conversation(
    model: Any,
    thread_id: str,
    effort: str,
    model_string: str = "",
    custom_providers: dict[str, Any] | None = None,
) -> tuple[Any, str | None, tuple[str, ...] | None]:
    """`model` as one conversation runs it: at its effort level, with that conversation's
    prompt-cache key; also the level it runs as and the levels it offers (None both when it
    takes none). `model_string` and `custom_providers` find it in the bundled catalog."""
    from .effort import catalog_levels, with_effort

    catalog = catalog_levels(model_string, custom_providers or {}) if model_string else None
    model, runs_as, levels = with_effort(model, effort, catalog)
    return with_prompt_cache_key(model, thread_id), runs_as, levels


def keeps_tool_list_fixed(model: str, custom_providers: dict[str, dict[str, str]]) -> bool:
    """Whether every built-in tool should be bound from the first request
    instead of found through search_tools.

    Binding all ~115 built-ins up front costs ~35k more tokens per request,
    which only pays off where a cache hit is nearly free and the window is
    large: DeepSeek charges 2% of a miss for a hit (deepseek-flash, ¥0.02
    vs ¥1 per 1M, checked 2026-10-05) and has a 1M-token window. The
    list stays fixed either way; this only decides how much of it is sent."""
    provider_key = model.split(":", 1)[0]
    return _is_deepseek(custom_providers.get(provider_key, {}).get("base_url", ""))


def _is_deepseek(base_url: str) -> bool:
    from urllib.parse import urlparse

    host = urlparse(base_url).hostname or ""
    return host == "deepseek.com" or host.endswith(".deepseek.com")


def _deepseek_chat_model_class() -> Any:
    """ChatOpenAI that keeps DeepSeek's `reasoning_content` and sends it
    back with each assistant message, which langchain-openai drops.

    DeepSeek requires it on every request that carries tools. Without it
    the server renders the previous turn differently once a new user
    message arrives, so each turn re-read the conversation uncached:
    measured, 10,478 of 11,246 prompt tokens missed at the next turn
    without it, 191 with it (ROADMAP Phase 8ck)."""
    from langchain_core.messages import AIMessage
    from langchain_openai import ChatOpenAI

    class ChatDeepSeek(ChatOpenAI):
        def _convert_chunk_to_generation_chunk(
            self,
            chunk: dict[str, Any],
            default_chunk_class: type,
            base_generation_info: dict[str, Any] | None,
        ) -> Any:
            generation = super()._convert_chunk_to_generation_chunk(
                chunk, default_chunk_class, base_generation_info
            )
            choices = chunk.get("choices") or [{}]
            reasoning = (choices[0].get("delta") or {}).get("reasoning_content")
            if generation is not None and reasoning:
                generation.message.additional_kwargs["reasoning_content"] = reasoning
            return generation

        def _create_chat_result(
            self, response: Any, generation_info: dict[str, Any] | None = None
        ) -> Any:
            result = super()._create_chat_result(response, generation_info)
            response_dict = response if isinstance(response, dict) else response.model_dump()
            for generation, choice in zip(
                result.generations, response_dict.get("choices") or [], strict=False
            ):
                reasoning = (choice.get("message") or {}).get("reasoning_content")
                if reasoning:
                    generation.message.additional_kwargs["reasoning_content"] = reasoning
            return result

        def _get_request_payload(
            self, input_: Any, *, stop: list[str] | None = None, **kwargs: Any
        ) -> dict[str, Any]:
            payload = super()._get_request_payload(input_, stop=stop, **kwargs)
            messages = self._convert_input(input_).to_messages()
            for message, sent in zip(messages, payload.get("messages", []), strict=False):
                reasoning = message.additional_kwargs.get("reasoning_content")
                if isinstance(message, AIMessage) and reasoning:
                    sent["reasoning_content"] = reasoning
            return payload

    return ChatDeepSeek
