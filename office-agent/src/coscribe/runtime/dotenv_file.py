"""Where `.env` lives and loading it into the real process environment, shared by the CLI and
the web server so both read the same file."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .secrets import resolve_env_keyring_refs


def app_data_dir() -> Path:
    """Per-user application-data directory -- the fallback dotenv_path
    below uses when the process has no meaningful project-directory cwd
    (office-agent-desktop's Electron shell spawns the sidecar with no
    natural project dir to look for a `.env` in, and the same is true
    running the PyInstaller-packaged binary directly). Same convention
    most desktop apps use: `%APPDATA%\\Coscribe` on Windows,
    `~/Library/Application Support/coscribe` on macOS,
    `~/.config/coscribe` elsewhere."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        return Path(base) / "Coscribe" if base else Path.home() / "coscribe"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "coscribe"
    return Path.home() / ".config" / "coscribe"


def dotenv_path() -> Path:
    """Where to load/write `.env`. Prefers a real, existing project-
    relative `./.env` -- the ordinary CLI/manually-run-web-server case,
    completely unchanged from before -- and only falls back to
    app_data_dir() (creating it if needed) when no such file exists,
    which is the normal case for office-agent-desktop's sidecar (no
    natural project cwd) or the packaged binary run directly. The
    Electron shell additionally spawns the sidecar with this same
    directory as its cwd (belt-and-suspenders, not required for this to
    work) -- so
    this fallback mainly matters for running the packaged binary on its
    own, e.g. this project's own PyInstaller smoke test."""
    cwd_env = Path(".env")
    if cwd_env.exists():
        return cwd_env
    app_data_env = app_data_dir() / ".env"
    app_data_env.parent.mkdir(parents=True, exist_ok=True)
    return app_data_env


def prepare_env() -> Path:
    """Shared first half of cli.py's _load_settings and web/app.py's _load_settings_or_none:
    resolves .env's real location and loads it into the real process
    environment, so both callers agree on the exact same file (see
    dotenv_path's own docstring for why that matters) and both get a
    real provider API key rather than a stale keyring-ref sentinel.

    Settings' own env_file only feeds its declared COSCRIBE_-prefixed
    fields; provider API keys (GEMINI_API_KEY etc.) are unprefixed and
    read directly from os.environ by each provider SDK, so .env needs to
    be loaded into the real process environment too, not just parsed by
    Settings -- see config.py's Settings docstring.
    """
    path = dotenv_path()
    # override=True: .env is the one place a double-click desktop app's
    # user can configure anything at all (no terminal to set a real
    # environment variable in) -- live-hit without this: a corporate
    # machine already had HTTP_PROXY/HTTPS_PROXY set at the Windows
    # user/system level (a security agent's local traffic-interception
    # relay, pointed at 127.0.0.1 rather than the real upstream proxy),
    # and python-dotenv's own default (override=False) silently kept
    # that stale value instead of the one the user had just written into
    # .env, with no error -- the Gemini call just failed to reach the
    # real proxy at all.
    load_dotenv(path, override=True)
    # A provider API key written by a previous run may be a keyring-ref
    # sentinel string rather than the real value (see runtime/secrets.py)
    # -- resolve it in the real process environment right here, the same
    # place .env just got loaded into it, so every downstream
    # os.getenv("ANTHROPIC_API_KEY")-style read (inside the SDKs
    # themselves) sees the real secret, never the sentinel.
    resolve_env_keyring_refs()
    return path
