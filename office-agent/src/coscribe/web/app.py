"""FastAPI app: serves the chat WebSocket protocol and the static frontend.

Built on runtime_lg (the LangGraph-based runtime -- see runtime_lg/README.md
for the full migration history).

Reuses the existing frontend (web/static/*) unmodified -- the WS wire
protocol was kept identical to the old runtime's on purpose throughout the
migration, see runtime_lg/README.md's research notes. Plan Mode/Accept-
Edits/Compact/Hooks are wired in via conversation/session.py -- see that module's
docstring and runtime_lg/README.md for the design (interrupt_on membership
doubling as the plan-mode-blocked set; all-tools interrupt gating when
PreToolUse hooks are configured; checkpointer-state compaction). MCP tools
go through runtime_lg/mcp.py's connect_mcp_tools_lg (langchain-mcp-
adapters), not the removed tools/connect_mcp_tools -- see that module's
docstring for why.

One real behavioral gap vs. the old runtime, **now closed for MCP
connectors specifically, still open for everything else**: config changes
elsewhere (a new custom provider, a new/removed skill) still only take
effect for the next new thread/session, not every
already-open one: runtime_lg's create_agent() compiles a fixed graph once
(model and tools baked in), so an already-open ChatSession keeps whatever it was built with
until its process restarts or a fresh thread_id is opened, unless
something explicitly rebuilds that graph in place.

MCP connectors got that explicit rebuild after a real, live-reported bug:
a user enabled a connector mid-conversation and it had no effect on that
same, already-open thread (confirmed against this exact "next new session
only" gap). add_mcp_server/remove_mcp_server/bump_mcp_server_version below
now all call ConnectorManager.refresh_all_sessions_extra_tools() after mutating
the manager's tools, which calls ChatSessionLG.refresh_extra_tools on every
currently-open session -- same "rebuild the compiled graph in place, same
checkpointer/thread_id" mechanism switch_model already used for models.
Providers/skills don't get the same treatment here: rebuilding
*every* open session's graph on *every* kind of config change is
meaningfully more work and risk than closing the one gap a real user
actually hit, so those remain "persists correctly, next session picks it
up," a decision made explicitly, not an oversight.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import logging
import os
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import dotenv_values, load_dotenv
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import ValidationError

from .. import __version__
from ..code_runtime import (
    remove_stale_code_sidecars,
    shutdown_code_services,
)
from ..config import Settings
from ..conversation import ChatSessionLG, ThreadMetaStore
from ..runtime import (
    LLMClient,
    empty_hooks_config,
    env_resolve_secret_for_display,
    load_custom_providers,
    load_hooks_config,
    prepare_env,
    resolve_env_keyring_refs,
    resolve_secret,
    run_hook,
)
from ..runtime import (
    dotenv_path as _dotenv_path,
)
from ..runtime_lg import (
    LoopbackCallback,
    McpOAuth,
    poll_due_scheduled_tasks,
    poll_due_wakes,
    reconcile_interrupted_runs,
)
from ..tools import (
    SkillInfo,
    enabled_skill_names,
    load_builtin_skills,
    load_skills,
    sweep_folder_grants,
)
from .background_events import BackgroundEventBus
from .connector_manager import ConnectorManager
from .environment_migration import migrate_to_environments
from .folder_grants import sweep_unused_folder_grants
from .local_guard import ALLOWED_HOSTS_ENV, LocalOnlyGuard, launch_token, page_with_token
from .provider_catalog import (
    BUILTIN_PROVIDERS,
)
from .routes import include_routers
from .routes.shared import _mask, _read_providers_raw
from .scheduler import Scheduler
from .setup_app import build_setup_app
from .state import AppState
from .thread_files import ThreadFiles


def _oauth_page(message: str) -> str:
    """The page a connector's sign-in redirects the browser to."""
    return (
        "<!doctype html><meta charset=utf-8><title>coscribe</title>"
        '<body style="font-family:system-ui,sans-serif;max-width:32rem;margin:20vh auto;'
        f'padding:0 1rem"><h2>coscribe</h2><p>{html.escape(message)}</p></body>'
    )


# How long lifespan() blocks app startup on connect_mcp_tools_lg before
# letting a still-connecting server finish in the background instead --
# see lifespan's own comment. Same default Claude Code itself settled on
# (MCP_CONNECT_TIMEOUT_MS) for the identical problem.
MCP_STARTUP_TIMEOUT_SECONDS = 5.0


STATIC_DIR = Path(__file__).parent / "static"


class _NoCacheStaticFiles(StaticFiles):
    """Plain StaticFiles lets browsers cache app.js/style.css/index.html
    with only heuristic (best-effort, not guaranteed-fresh) revalidation --
    fine for a CDN-fronted public site, but this is a single local process
    whose static assets change on every `git pull` + restart, with nothing
    else forcing a refetch (no hashed filenames, no version query param).
    A stale-cached app.js after a redeploy is worse than it sounds: this
    script is one flat top-to-bottom file, so a single DOM id it references
    that a newer index.html has moved or removed throws partway through and
    silently kills every listener registered after that point -- which
    looks exactly like "nothing responds to clicks" with no visible error.
    """

    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store"
        return response


# A small, curated, hardcoded list -- not a live marketplace. Every entry is
# a hosted (remote) MCP server the user signs in to in their own browser:
# nothing is installed, no app is registered, and no company IT step is
# needed, so it works wherever the person can already open the service
# themselves. Each one was checked against the live server (2026-10-07): the
# registration call is accepted and the sign-in page is reached. A server that
# needs a pre-registered app -- Slack, Google Workspace, Box, HubSpot, and
# Dropbox, which lists a registration address but answers "only pre-registered
# trusted partners" -- or a company-approved app, like Microsoft 365 in a
# tenant that doesn't allow third-party apps, is left out on purpose.
# Anything else is still addable by hand from the Custom tab.
# git/github catalog entries (local git ops via mcp-server-git; GitHub
# issues/PRs/repo search via GitHub's own remote MCP server + an OAuth
# Device Flow sign-in) existed here and were removed -- coscribe's target
# user is a general office file/task automation assistant, not a developer
# tool. The Microsoft 365 entry (a community server run locally with npx,
# signing in by device code) was removed for the reasons above. Still
# addable by hand via the Connectors panel's Custom tab.

# Well-maintained official MCP servers that exist but are deliberately left
# out of MCP_CATALOG above -- these don't just need a path/token filled in
# via the Custom-tab prefill flow, they either overlap with an existing
# coscribe capability or raise a maintenance concern:
#   - Filesystem (npm `@modelcontextprotocol/server-filesystem`) -- overlaps
#     with coscribe's own workspace-scoped file tools
#   - Postgres (npm `@modelcontextprotocol/server-postgres`) -- its latest
#     release (0.6.2, not this repo's 2026.x calendar-versioned releases)
#     suggests it's seen less recent maintenance than the others above
# Both are still addable today via the Connectors panel's Custom tab (name +
# command + args + env) for anyone who wants them anyway.


def _load_settings_or_none() -> Settings | None:
    """None instead of an error exit on a config ValidationError, so main() falls into first-run
    setup mode rather than crashing on a fresh install with no default model or API key yet; the
    CLI's _load_settings still exits, since a terminal is the right place to fix .env by hand."""
    path = prepare_env()
    try:
        return Settings(_env_file=path)  # type: ignore[call-arg]
    except ValidationError:
        return None


def create_setup_app(configured: asyncio.Future[Settings]) -> FastAPI:
    return build_setup_app(configured, _dotenv_path, _load_settings_or_none)


async def _start_mcp_connect(
    settings: Settings, mcp_oauth: Any, connectors: ConnectorManager
) -> asyncio.Task[Any] | None:
    """Connect the configured MCP servers, waiting only up to the startup timeout; a slow one
    finishes in the background. Returns the still-running task, if any, for shutdown to cancel."""
    mcp_connect_task: asyncio.Task[Any] | None = None
    if settings.mcp_config_path is not None:
        # Real, user-reported bug: this used to be a plain
        # `await connect_mcp_tools_lg(...)`, so the app didn't
        # start serving *anything* -- not even the splash/setup
        # page -- until every configured MCP server finished
        # connecting. A slow-to-start one (Playwright launching a
        # real browser process is the worst case) meant a real,
        # repeatable multi-minute wait on every single cold
        # start, unrelated to which desktop shell was used.
        # Mirrors Claude Code's own real fix for the identical
        # problem (MCP_CONNECT_TIMEOUT_MS, default 5s): wait up
        # to MCP_STARTUP_TIMEOUT_SECONDS, then stop blocking
        # startup on it -- asyncio.shield() keeps the connect
        # task itself running rather than cancelling it just
        # because this wait_for gave up on it.
        # Deferred import -- see the top-of-file comment above MCP_STARTUP_TIMEOUT_SECONDS.
        from ..runtime_lg import connect_mcp_tools_lg

        connect_task: asyncio.Task[Any] = asyncio.create_task(
            connect_mcp_tools_lg(
                settings.mcp_config_path,
                mcp_oauth.auth_for,
                connectors.reconnect_stale_connector,
                state_dir=settings.state_dir,
            )
        )
        mcp_connect_task = connect_task
        try:
            tools, connections = await asyncio.wait_for(
                asyncio.shield(connect_task), timeout=MCP_STARTUP_TIMEOUT_SECONDS
            )
            connectors.tools = tools
            connectors.connections.update(connections)
            mcp_connect_task = None
        except TimeoutError:
            # Still connecting -- let the app start serving
            # requests now (a session opened in this window
            # simply starts with fewer tools, same as any
            # mid-conversation connector add/remove already
            # behaves) and splice the result in once it's ready,
            # reusing the exact mechanism a live connector-add
            # already uses to reach already-open sessions.
            async def _finish_mcp_connect_in_background(
                task: asyncio.Task[Any],
            ) -> None:
                try:
                    tools, connections = await task
                except Exception:
                    logging.getLogger(__name__).exception(
                        "connect_mcp_tools_lg: background connect failed"
                    )
                    return
                connectors.tools = connectors.tools + tools
                connectors.connections.update(connections)
                await connectors.refresh_all_sessions_extra_tools()

            asyncio.create_task(_finish_mcp_connect_in_background(connect_task))
    return mcp_connect_task


def _make_lifespan(
    settings: Settings,
    checkpoint_path: Path,
    checkpointer_holder: dict[str, Any],
    connectors: ConnectorManager,
    mcp_oauth: Any,
    scheduler: Scheduler,
    app_callback: Any,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        remove_stale_code_sidecars(settings.state_dir)
        # icacls on a large folder takes a while, and nothing waits on it.
        sweep = asyncio.create_task(asyncio.to_thread(sweep_unused_folder_grants, settings))
        async with AsyncSqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
            checkpointer_holder["checkpointer"] = checkpointer
            await migrate_to_environments(settings, checkpointer)
            mcp_connect_task = await _start_mcp_connect(settings, mcp_oauth, connectors)
            interrupted = reconcile_interrupted_runs(settings.state_dir)
            if interrupted:
                logging.getLogger(__name__).warning(
                    "Marked %d scheduled run(s) as failed -- still running at startup, "
                    "left over from a previous process that didn't shut down cleanly.",
                    interrupted,
                )
            swept = await scheduler.sweep_orphaned_run_threads()
            if swept:
                logging.getLogger(__name__).info(
                    "Deleted %d scheduled-run conversation(s) whose task or run record is gone.",
                    swept,
                )
            scheduler.start()
            yield
            await scheduler.stop()
            if mcp_connect_task is not None and not mcp_connect_task.done():
                mcp_connect_task.cancel()
                try:
                    await mcp_connect_task
                except (asyncio.CancelledError, Exception):
                    pass
            # Each connection now owns a real, persistent subprocess (see
            # runtime_lg/mcp.py's module docstring) -- close them all here
            # rather than letting them leak past this process's own
            # shutdown (a lingering Playwright browser, most visibly).
            for connection in connectors.connections.values():
                await connection.close()
            for task in list(connectors.sign_in_tasks):
                task.cancel()
            await app_callback.stop()
            await shutdown_code_services()
            await asyncio.gather(sweep, return_exceptions=True)

    return lifespan


def _configured_models(settings: Settings) -> list[str]:
    return [
        f"{name}:{info['default_model']}"
        for name, info in _providers_info(settings).items()
        if info["default_model"]
    ]


def _providers_info(settings: Settings) -> dict[str, Any]:
    env_values = dotenv_values(".env")
    # Fallback for an existing .env from before /api/setup started also
    # writing the per-provider default (see setup() above) -- without
    # this, a provider whose own COSCRIBE_<X>_DEFAULT_MODEL was never
    # set (true for whichever provider first-run setup picked, on any
    # .env written before that fix) silently vanishes from this list,
    # and therefore from the model switcher, the moment a *different*
    # provider becomes the active model and this one is no longer
    # rendered via the switcher's own currentModel-prop fallback.
    default_provider_key, _, default_model_fallback = (
        env_values.get("COSCRIBE_DEFAULT_MODEL") or ""
    ).partition(":")
    result: dict[str, Any] = {}
    for provider in BUILTIN_PROVIDERS:
        api_key = env_resolve_secret_for_display(env_values.get(provider["api_key_env"])) or ""
        if not api_key:
            continue
        default_model = env_values.get(provider["default_model_env"]) or ""
        if not default_model and provider["key"] == default_provider_key:
            default_model = default_model_fallback
        result[provider["key"]] = {
            "base_url": None,
            "default_model": default_model,
            "masked_key": _mask(api_key),
            "builtin": True,
        }
    if settings.providers_config_path is not None and settings.providers_config_path.is_file():
        raw = _read_providers_raw(settings.providers_config_path)
        for name, entry in raw["providers"].items():
            api_key = resolve_secret(entry.get("api_key")) or ""
            result[name] = {
                "base_url": entry.get("base_url", ""),
                "default_model": entry.get("default_model", ""),
                "masked_key": _mask(api_key) if api_key else None,
                "builtin": False,
            }
    return result


def create_app_lg(settings: Settings | None = None) -> FastAPI:
    # Same reasoning as create_app: each provider SDK's own os.getenv() call
    # needs unprefixed keys in the real process environment, which Settings'
    # own env_file parsing doesn't provide. Same dotenv_path() the CLI's
    # settings loading uses -- main() below always passes
    # settings explicitly (via _load_settings), so this branch only runs for
    # a caller that constructs the app directly with settings=None.
    dotenv_path = _dotenv_path()
    # override=True: see cli.py's _load_settings docstring -- a stale
    # ambient HTTP_PROXY/HTTPS_PROXY (or any other var) already set at
    # the OS level must not silently beat what the user actually wrote
    # into .env. Redundant, harmless work for anything _load_settings()
    # (cli.py) already resolved earlier in this same process (main()
    # below always calls that first); real work for a caller that
    # constructs the app directly with settings=None, skipping that path
    # entirely. See runtime/secrets.py's resolve_env_keyring_refs.
    load_dotenv(dotenv_path, override=True)
    resolve_env_keyring_refs()
    settings = settings or Settings(_env_file=dotenv_path)  # type: ignore[call-arg]

    hooks_config: dict[str, list[str]] = empty_hooks_config()
    if settings.hooks_config_path is not None:
        hooks_config = load_hooks_config(settings.hooks_config_path)

    custom_providers: dict[str, dict[str, str]] = {}
    if settings.providers_config_path is not None:
        custom_providers = load_custom_providers(settings.providers_config_path)
    # Only used for its get_context_window() heuristic (see session.py) --
    # the old runtime's LLMClient.complete()/complete_stream() are never
    # called from this app, resolve_chat_model's LangChain models are. Kept
    # live-updated via register_custom_provider/deregister_custom_provider
    # in add_provider/remove_provider below (same calls web/app.py's client
    # already gets), even though the *chat* model for a new session is
    # resolved fresh from disk instead -- see _get_session below.
    context_window_client = LLMClient(custom_providers=custom_providers)

    checkpoint_path = settings.state_dir / "runtime_lg_checkpoints.sqlite"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    sessions: dict[str, ChatSessionLG] = {}
    meta_store = ThreadMetaStore(settings.state_dir)
    # Set once the lifespan context is entered -- plain mutable holders
    # rather than module/globals, since create_app_lg() may be called more
    # than once (e.g. once per test). checkpointer_holder is always
    # populated before the app starts serving requests (see lifespan
    # below) -- _get_session is only reachable from ws_endpoint, which
    # can't run until the lifespan's own yield has happened.
    #
    # connectors.tools does NOT have that same guarantee, deliberately:
    # see lifespan's own MCP-connect comment for why a session opened
    # very early may briefly see fewer tools than a slow-to-connect MCP
    # server will eventually provide.
    checkpointer_holder: dict[str, Any] = {}
    # Fan-out for background-completion events (see background_events.py's
    # module docstring) -- the desktop shell's SSE client is the only
    # subscriber today, but this is a plain broadcaster, not a single-slot
    # holder, so nothing stops a future second subscriber.
    background_events = BackgroundEventBus()
    mcp_oauth = McpOAuth(settings.state_dir)
    connectors = ConnectorManager(settings, sessions, mcp_oauth.auth_for)

    def _oauth_callback_response(
        state: str, code: str | None, error: str | None
    ) -> tuple[int, str]:
        name = mcp_oauth.complete(state, code, error)
        if name is None:
            return 400, _oauth_page("This sign-in link has expired. Start again from coscribe.")
        if error:
            return 200, _oauth_page(f"Signing in to {name} didn't work: {error}.")
        return 200, _oauth_page(
            f"You're signed in to {name}. You can close this tab and go back to coscribe."
        )

    app_callback = LoopbackCallback(_oauth_callback_response)
    thread_files = ThreadFiles(settings)

    def _skills_by_name() -> dict[str, SkillInfo]:
        # Re-scanned on every call, not a closure snapshot -- the same
        # staleness bug switch_model's custom-providers snapshot had (see
        # runtime_lg/README.md), just for skills: settings.skills_dir can
        # gain a new entry mid-process now (POST /api/skills/upload
        # below), and both GET /api/skills and the select_skills WS
        # validation need to see it without a server restart. Skill
        # directories are few and cheap to stat, so re-scanning per call
        # (rather than invalidating a cache on upload) is the simplest
        # correct thing.
        return {s.name: s for s in load_builtin_skills() + load_skills(settings.skills_dir)}

    # load_skills(settings.skills_dir) above creates the directory as a
    # side effect (see skills.py's _scan_skills_dir) -- that used to
    # happen for free the moment the old eager `skills_by_name = {...}`
    # snapshot was built at startup. Now that the scan is lazy (only on
    # an actual GET/WS call), nothing guarantees it exists yet -- e.g.
    # /api/browse-dirs listing settings.workspace_root right after
    # startup, before any skills endpoint has ever been hit, wouldn't
    # see it. One throwaway call here keeps that startup-time side
    # effect intact without bringing back the staleness bug.
    _skills_by_name()

    def _enabled_skills() -> set[str]:
        # One global on/off per skill (Settings > Skills), read fresh so a
        # toggle applies to the next session without a restart.
        return enabled_skill_names(settings.skills_dir, settings.state_dir)

    def _get_session(thread_id: str) -> ChatSessionLG:
        if thread_id not in sessions:
            # Re-read providers.json fresh for every *new* session (unlike
            # context_window_client's fixed custom_providers above) -- the
            # cheapest way to get "a provider added after startup is usable
            # in the next new thread" without a second holder to keep in
            # sync, and this file only ever runs once per new thread_id, not
            # once per message.
            session_custom_providers = (
                load_custom_providers(settings.providers_config_path)
                if settings.providers_config_path is not None
                else {}
            )
            session_start_payload = {
                "event": "SessionStart",
                "agent_name": "coordinator",
                "thread_id": thread_id,
            }
            for command in hooks_config["SessionStart"]:
                run_hook(command, session_start_payload)
            folders = thread_files.resolve_folders(thread_id)
            sessions[thread_id] = ChatSessionLG(
                thread_id=thread_id,
                settings=settings,
                context_window_client=context_window_client,
                custom_providers=session_custom_providers,
                extra_tools=connectors.session_extra_tools(),
                checkpointer=checkpointer_holder["checkpointer"],
                hooks_config=hooks_config,
                enabled_skill_names=_enabled_skills(),
                workspace_root=folders[0] if folders else settings.workspace_root,
                workspace_explicit=bool(folders),
                extra_folders=folders[1:],
                configured_models=lambda: _configured_models(settings),
            )
        return sessions[thread_id]

    async def _get_session_async(thread_id: str) -> ChatSessionLG:
        # poll_due_wakes takes an async get_session callback (see its own
        # docstring for why -- runtime_lg can't import ChatSessionLG
        # directly, that would be circular) -- _get_session itself is
        # plain sync, this is just the async wrapper it needs.
        return _get_session(thread_id)

    async def _delete_thread_data(thread_id: str) -> bool:
        """Delete a thread's checkpoints plus every sidecar file that belongs
        to it -- otherwise a new thread later reusing the same id would
        inherit an old task list or workspace/skills choice. Returns
        whether any checkpoint existed."""
        checkpointer = checkpointer_holder["checkpointer"]
        await checkpointer.setup()  # see list_threads' identical comment
        cursor = await checkpointer.conn.execute(
            "SELECT 1 FROM checkpoints WHERE thread_id = ? LIMIT 1", (thread_id,)
        )
        existed = await cursor.fetchone() is not None
        await checkpointer.adelete_thread(thread_id)
        thread_files.delete(thread_id)
        ThreadMetaStore(settings.state_dir).delete(thread_id)
        sessions.pop(thread_id, None)
        return existed

    scheduler = Scheduler(
        settings,
        sessions,
        background_events,
        _get_session_async,
        _delete_thread_data,
        lambda: checkpointer_holder["checkpointer"],
        poll_due_wakes,
        poll_due_scheduled_tasks,
    )

    app = FastAPI(
        lifespan=_make_lifespan(
            settings,
            checkpoint_path,
            checkpointer_holder,
            connectors,
            mcp_oauth,
            scheduler,
            app_callback,
        )
    )
    app.add_middleware(LocalOnlyGuard, token=(token := launch_token()))
    # On app.state so tests publish to the bus _wake_poll_loop uses without
    # going through the SSE endpoint, which never completes.
    app.state.background_events = background_events

    @app.get("/")
    async def index() -> Response:
        return page_with_token(STATIC_DIR / "index.html", token)

    state = AppState(
        settings=settings,
        context_window_client=context_window_client,
        meta_store=meta_store,
        sessions=sessions,
        checkpointer_holder=checkpointer_holder,
        background_events=background_events,
        mcp_connections=connectors.connections,
        mcp_oauth=mcp_oauth,
        app_callback=app_callback,
        sign_in_tasks=connectors.sign_in_tasks,
        get_session=_get_session,
        get_session_async=_get_session_async,
        session_extra_tools=connectors.session_extra_tools,
        skills_by_name=_skills_by_name,
        providers_info=lambda: _providers_info(settings),
        connector_tools=connectors.connector_tools,
        connect_and_register_mcp_server_lg=connectors.connect_and_register_mcp_server_lg,
        disconnect_mcp_server_lg=connectors.disconnect_mcp_server_lg,
        refresh_all_sessions_extra_tools=connectors.refresh_all_sessions_extra_tools,
        oauth_callback_response=_oauth_callback_response,
        thread_files=thread_files,
        delete_thread_data=_delete_thread_data,
        delete_run_threads=scheduler.delete_run_threads,
        execute_and_announce=scheduler.execute_and_announce,
        announce_run=scheduler.announce_run,
        track_background=scheduler.track_background,
    )
    include_routers(app, state)

    app.mount("/static", _NoCacheStaticFiles(directory=STATIC_DIR), name="static")

    return app


def _watch_parent_windows(parent_pid: int) -> None:
    """Windows half of _exit_when_orphaned -- there's no re-parenting
    signal to poll, so this blocks on a handle to the parent process and
    exits the moment it's actually signaled. Best-effort: this is
    defense-in-depth on top of office-agent-desktop's own
    RunEvent::Exit/RunEvent::ExitRequested child.kill(), which is the
    primary cleanup path regardless of whether this succeeds.

    Two correctness details, not obvious from the WinAPI docs alone:
    OpenProcess returns a 64-bit HANDLE, but ctypes defaults a function's
    return type to a 32-bit int -- without explicit restype/argtypes the
    handle gets silently truncated to garbage. And only WAIT_OBJECT_0
    means the parent genuinely terminated; a bad/invalid handle yields
    WAIT_FAILED immediately, and treating that the same as "parent died"
    would kill a perfectly healthy sidecar moments after it starts."""
    import ctypes
    import threading
    from ctypes import wintypes

    synchronize = 0x0010_0000
    wait_object_0 = 0x0000_0000

    # typeshed's ctypes stub only defines WinDLL under sys.platform == "win32" --
    # this repo's mypy always runs on Linux/macOS dev machines, where the stub
    # doesn't expose it at all, even though this function itself only ever runs
    # on real Windows (guarded by the caller's own sys.platform check above).
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

    handle = kernel32.OpenProcess(synchronize, False, parent_pid)
    if not handle:
        return

    def watch() -> None:
        if kernel32.WaitForSingleObject(handle, 0xFFFF_FFFF) == wait_object_0:
            os._exit(0)

    threading.Thread(target=watch, daemon=True).start()


def _exit_when_orphaned() -> None:
    """When launched as office-agent-desktop's sidecar
    (COSCRIBE_EXIT_WITH_PARENT=1, set by the Electron shell -- or the
    now-legacy Tauri shell before it, which set the same flag -- when it
    spawns this process), exit if the parent dies -- even on an abrupt
    crash that skips the shell's own graceful kill of this process on
    quit. A no-op for the ordinary
    CLI/browser case (the env var is unset), and never runs at all
    unless a desktop shell opted in.

    COSCRIBE_PARENT_PID is the shell's own PID, passed explicitly
    rather than relying on os.getppid() alone. office-agent-desktop's
    packaging deliberately uses PyInstaller --onedir (see packaging/
    coscribe_server.spec's own docstring) specifically to avoid
    onefile's bootloader-in-the-middle problem, so getppid() would
    already point at the right process here -- but watching the
    explicit PID costs nothing and stays correct even if that changes.

    POSIX: poll the PID with kill(pid, 0) -- a liveness probe, no signal
    actually delivered. Windows has no equivalent, see
    _watch_parent_windows above."""
    if os.environ.get("COSCRIBE_EXIT_WITH_PARENT") != "1":
        return
    try:
        parent_pid = int(os.environ.get("COSCRIBE_PARENT_PID") or 0)
    except ValueError:
        parent_pid = 0
    parent_pid = parent_pid or os.getppid()

    if sys.platform == "win32":
        _watch_parent_windows(parent_pid)
        return

    import threading
    import time

    def watch() -> None:
        while True:
            time.sleep(1.5)
            try:
                os.kill(parent_pid, 0)
            except ProcessLookupError:
                os._exit(0)
            except PermissionError:
                pass  # alive, just owned by someone else -- keep watching

    threading.Thread(target=watch, daemon=True).start()


async def _run_web_server(host: str, port: int) -> None:
    """Runs the setup app (create_setup_app) until it has a usable
    Settings, then the real app (create_app_lg) -- both `uvicorn.Server`
    instances bound to the same host/port, one after the other, never at
    once. Managed by hand instead of the simpler `uvicorn.run(app, ...)`
    used before this existed, specifically so this same process/PID can
    serve two different apps in sequence -- see create_setup_app's own
    docstring for why an actual process restart isn't safe here."""
    settings = _load_settings_or_none()
    if settings is None:
        configured: asyncio.Future[Settings] = asyncio.get_running_loop().create_future()
        setup_server = uvicorn.Server(
            uvicorn.Config(create_setup_app(configured), host=host, port=port)
        )
        serve_task = asyncio.create_task(setup_server.serve())
        settings = await configured
        # Releases the port before the real app tries to bind it below --
        # sequential, not concurrent, so there's no double-bind to race.
        setup_server.should_exit = True
        await serve_task

    logging.basicConfig(level=settings.log_level)
    # No access log: it would print the launch token a WebSocket carries in its URL.
    await uvicorn.Server(
        uvicorn.Config(create_app_lg(settings), host=host, port=port, access_log=False)
    ).serve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run coscribe's local web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    # Not used by anything at runtime -- exists so the packaged desktop
    # shell's installer can execute this binary once, immediately after
    # extraction, purely to make it exit instantly instead of actually
    # starting a server (which would bind a port and run forever). Real,
    # live-reported problem this addresses: Windows Defender's real-time
    # scan of a large, unsigned, freshly-extracted exe on its very first
    # execution can take long enough to look like the app hung -- the
    # splash page's own 180s failure UI would fire, sidecar log
    # completely empty the whole time, every single fresh install/update
    # ("每次新包第一次运行都是要启动很久"). Triggering that same one-time
    # scan-and-cache cost during the install step (where a moment's delay
    # is already expected and shown as installer progress) instead of at
    # the user's first real launch fixes the *experience*, not the
    # underlying OS/AV cost -- see
    # office-agent-desktop-electron/build/installer.nsh, which is what
    # actually calls this.
    parser.add_argument("--version", action="version", version=f"coscribe {__version__}")
    # Run by the uninstaller: the ACEs scripts' isolation wrote on the person's folders go too.
    parser.add_argument("--revoke-folder-grants", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.revoke_folder_grants:
        settings = _load_settings_or_none()
        if settings is not None:
            sweep_folder_grants(settings.state_dir, None)
        return

    _exit_when_orphaned()
    if args.host not in ("127.0.0.1", "localhost", "::1", "0.0.0.0", "::"):
        # Served under its own name on purpose: the Host check must accept it.
        os.environ[ALLOWED_HOSTS_ENV] = ",".join(
            filter(None, [os.environ.get(ALLOWED_HOSTS_ENV, ""), args.host])
        )
    asyncio.run(_run_web_server(args.host, args.port))


if __name__ == "__main__":
    main()
