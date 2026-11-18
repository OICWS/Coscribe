"""MCP (Model Context Protocol) server config parsing.

Loads a Claude-Desktop-style `mcpServers` JSON config and validates each
entry. Connecting to the servers themselves happens in runtime_lg/mcp.py,
via langchain-mcp-adapters -- not aisuite's own MCPClient, whose
MCPToolWrapper collapses each tool's real JSON Schema into a lossy generic
Python signature (see runtime_lg/README.md's "MCP tools under runtime_lg"
section for the live-reproduced bug this caused). This module used to
also hold that aisuite-based connector, deleted once runtime_lg's own
connector fully replaced it -- see runtime_lg/README.md's "audit + delete
old runtime" section.

`validate_mcp_config`/`MCPConfig` below used to be
`aisuite.mcp.config.validate_mcp_config`, reused purely as a validator
(never tied to aisuite's own MCP client). Real, measured startup-time
finding: profiling `coscribe-web-lg`'s known-slow startup
(`python -X importtime`) found that one `from aisuite.mcp.config import
...` here cost ~485ms on its own -- not because that submodule itself is
heavy (it's pure `typing`, zero third-party deps, confirmed by reading
it), but because importing *any* submodule of a package always runs that
package's own `__init__.py` first, and aisuite's pulls in its full
`Client`/`ProviderFactory`/`MCPClient` machinery (which itself imports the
entire `mcp` SDK a second time -- langchain-mcp-adapters, used by
runtime_lg/mcp.py's real connector, already needs `mcp` too, so this was
pure duplicate weight). None of that machinery was ever used here -- this
module only ever wanted the validator function. Vendored a minimal
equivalent below instead of depending on aisuite for it, dropping the
~485ms. Deliberately narrower than aisuite's own version: aisuite's schema
also validates/normalizes `allowed_tools`/`use_tool_prefix`/
`timeout_seconds`/`response_bytes_cap`/`lazy_connect` -- confirmed via
grep that nothing downstream of `load_mcp_server_configs` (runtime_lg/
mcp.py's `_to_lg_connection`, web/app.py's MCP endpoints) ever reads any
of those fields, so validating them was already dead weight even before
this change; only the fields actually used to establish a connection
(`command`/`args`/`env`/`cwd`/`server_url`/`headers`) are validated here.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, TypedDict, cast
from urllib.parse import unquote, urlsplit

from ..runtime import (
    MIN_VALUE,
    SecretError,
    SecretStore,
    host_allowed,
    placeholders_in,
    resolve_secret,
    substitute,
)
from .exec import resolve_python_command

logger = logging.getLogger(__name__)


class MCPConfig(TypedDict, total=False):
    """The subset of aisuite's MCPConfig shape runtime_lg/mcp.py's
    `_to_lg_connection` actually reads -- see this module's docstring for
    why the fuller aisuite schema isn't reproduced here."""

    type: str
    name: str
    command: str
    args: list[str]
    env: dict[str, str]
    cwd: str
    server_url: str
    headers: dict[str, str]
    auth: str
    oauth_app: str


def validate_mcp_config(config: dict[str, Any]) -> MCPConfig:
    """Validate one `mcpServers` entry (already tagged with `type`/`name`
    by `load_mcp_server_configs` below) and return it as a normalized
    `MCPConfig`. Raises `ValueError` with a message naming the actual
    problem, same contract aisuite's own `validate_mcp_config` had."""
    if config.get("type") != "mcp":
        raise ValueError(f"Invalid config type: {config.get('type')}. Expected 'mcp'")

    name = config.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"MCP 'name' must be a non-empty string, got: {name!r}")

    has_stdio = "command" in config
    has_http = "server_url" in config
    if not (has_stdio ^ has_http):
        raise ValueError(
            "MCP config must have either 'command' or 'server_url'. "
            "Use one or the other to specify transport type."
        )

    normalized: MCPConfig = {"type": "mcp", "name": name}
    if has_stdio:
        command = config["command"]
        if not isinstance(command, str):
            raise ValueError(f"MCP 'command' must be a string, got: {type(command)}")
        args = config.get("args", [])
        if not isinstance(args, list):
            raise ValueError(f"MCP 'args' must be a list, got: {type(args)}")
        normalized["command"] = command
        normalized["args"] = args
        if "env" in config:
            env = config["env"]
            if not isinstance(env, dict):
                raise ValueError(f"MCP 'env' must be a dict, got: {type(env)}")
            normalized["env"] = env
        if "cwd" in config:
            normalized["cwd"] = config["cwd"]
    else:
        server_url = config["server_url"]
        if not isinstance(server_url, str):
            raise ValueError(f"MCP 'server_url' must be a string, got: {type(server_url)}")
        if not (server_url.startswith("http://") or server_url.startswith("https://")):
            raise ValueError(
                f"MCP 'server_url' must start with http:// or https://, got: {server_url}"
            )
        normalized["server_url"] = server_url
        if "headers" in config:
            headers = config["headers"]
            if not isinstance(headers, dict):
                raise ValueError(f"MCP 'headers' must be a dict, got: {type(headers)}")
            normalized["headers"] = headers
        if "auth" in config:
            if config["auth"] != "oauth":
                raise ValueError(f"MCP 'auth' must be 'oauth' if given, got: {config['auth']!r}")
            if "headers" in config:
                raise ValueError("MCP 'auth' and 'headers' can't be used together")
            normalized["auth"] = "oauth"
            if "oauth_app" in config:
                app = config["oauth_app"]
                if not isinstance(app, str) or not app.strip():
                    raise ValueError(f"MCP 'oauth_app' must be a non-empty string, got: {app!r}")
                normalized["oauth_app"] = app

    return normalized


def with_secrets(config: MCPConfig, state_dir: Path | None) -> MCPConfig:
    """`config` with each `{{secret:NAME}}` in its env and header values
    replaced by that secret's value from Settings > Secrets, so the value
    lives only in the keychain and never in mcp.json. A header goes only to
    this connector's own server, so the secret must be one allowed for that
    host; an env value goes to the local command the user chose, which has
    no host to check. Raises SecretError, naming the connector and secret."""
    resolved: dict[str, Any] = dict(config)
    host = urlsplit(config["server_url"]).hostname if "server_url" in config else None
    for field in ("env", "headers"):
        values: dict[str, str] | None = config.get(field)  # type: ignore[assignment]
        if not values:
            continue
        resolved[field] = {
            key: _substitute_secrets(
                config["name"], field, value, host if field == "headers" else None, state_dir
            )
            for key, value in values.items()
        }
    return cast(MCPConfig, resolved)


def prepare_for_connect(config: MCPConfig, state_dir: Path | None) -> MCPConfig:
    """`config` as the connection needs it: keychain references read back and
    secret placeholders filled in. Raises SecretError or RuntimeError."""
    prepared: dict[str, Any] = dict(config)
    for field in ("env", "headers"):
        values: dict[str, Any] | None = config.get(field)  # type: ignore[assignment]
        if values:
            prepared[field] = {k: resolve_secret(v) or "" for k, v in values.items()}
    ready = with_secrets(cast(MCPConfig, prepared), state_dir)
    _blank_credentials(ready)
    return with_interpreter(ready, state_dir)


# Parts of an env or header name that say its value is a credential, so a server that echoes
# it must not put it in front of the model. Others (NODE_ENV, a path, a base URL, Content-Type)
# stay readable: blanking them would hide them from every tool result in the process.
_CREDENTIAL_PARTS = frozenset(
    {
        "auth", "authorization", "bearer", "cookie", "cred", "creds", "credential",
        "credentials", "pass", "passwd", "password", "pat", "pwd", "secret", "session",
        "signature", "token",
    }
)  # fmt: skip
_CREDENTIAL_ENDINGS = ("key", "token", "secret", "password")
_TOKEN_SHAPED = re.compile(r"[A-Za-z0-9_\-.+=]{20,}")


def _name_parts(name: str) -> list[str]:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()
    return [part for part in re.split(r"[^a-z0-9]+", words) if part]


def _looks_like_token(value: str) -> bool:
    return bool(
        _TOKEN_SHAPED.fullmatch(value) and re.search(r"[A-Za-z]", value) and re.search(r"\d", value)
    )


def _is_credential(name: str, value: str) -> bool:
    """Whether a connector's env or header value is kept like a secret: its name says so,
    or the value itself looks like a token (long, letters and digits, no path or URL)."""
    parts = _name_parts(name)
    if any(part in _CREDENTIAL_PARTS or part.endswith(_CREDENTIAL_ENDINGS) for part in parts):
        return True
    return _looks_like_token(value)


# A connection string carries its password inside a value whose name says nothing (DATABASE_URL,
# a command-line argument), and a server that cannot connect tends to print that string back.
# Only a URL's `user:password`, a token used as its user name, and `name=value` parts named like
# a credential are taken out; the host, path, a user name on its own and other options stay
# readable.
# A URL ends at whitespace, a quote, or a comma that starts the next URL (a list of hosts).
_URL_IN_TEXT = re.compile(
    r"[A-Za-z][A-Za-z0-9+.-]*://[^\s\"'<>]+?(?=,[A-Za-z][A-Za-z0-9+.-]*://|[\s\"'<>]|$)"
)
_NAMED_PART = re.compile(
    r"(?:^|[;&?#\s])-{0,2}([A-Za-z][A-Za-z0-9_.-]*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^;&#\s\"']+)"
)
# An ADO.NET or ODBC string: `Name With Spaces=value up to the semicolon;`, a value that holds a
# semicolon quoted or braced.
_ADO_PART = re.compile(
    r"(?:^|;)\s*([A-Za-z][A-Za-z0-9 _.]*?)\s*=\s*"
    r"(\"(?:[^\"]|\"\")*\"|'(?:[^']|'')*'|\{[^}]*\}|[^;]*)"
)
# Narrower than _CREDENTIAL_PARTS: an option such as authSource=admin, sslkey=/path/to/client.key,
# --sort-key=created_at or --key-file names no value worth hiding. `key` counts only alone (a
# query string's ?key=) or as an API or access key.
_PART_NAMES = frozenset(
    {"password", "passwd", "pwd", "pass", "secret", "token", "apikey", "sig", "signature"}
)
_PART_ENDINGS = ("password", "secret", "token")
_KEY_NAMES = ("apikey", "accesskey", "subscriptionkey")
# A name ending in one of these points at where a credential is, not at the credential.
_NOT_THE_VALUE = frozenset({"file", "path", "dir", "env", "var", "name", "id", "type", "mode"})
_PATH_SHAPED = re.compile(r"(?:[/~]|\.{1,2}[/\\]|[A-Za-z]:[/\\]|\\\\)")
_FLAG = re.compile(r"-{1,2}([A-Za-z][A-Za-z0-9_-]*)")


def _names_a_credential_part(name: str) -> bool:
    parts = _name_parts(name)
    if not parts or parts[-1] in _NOT_THE_VALUE:
        return False
    joined = "".join(parts)
    if joined == "key" or joined.endswith(_KEY_NAMES):
        return True
    return any(part in _PART_NAMES or part.endswith(_PART_ENDINGS) for part in parts)


def _with_decoded(value: str) -> list[str]:
    return [value, unquote(value)] if value else []


def _part_value(raw: str) -> list[str]:
    value = raw.strip()
    if len(value) >= 2 and (value[0], value[-1]) in {('"', '"'), ("'", "'"), ("{", "}")}:
        value = value[1:-1]
    if _PATH_SHAPED.match(value):
        return []
    return _with_decoded(value)


def _userinfo(url: str) -> str:
    """The `user:password` of `url`, parsed by hand: urlsplit raises on a broken host such as
    `http://[fe80::1`, and stops a password at a raw `/`, `?` or `#`."""
    rest = url.split("://", 1)[1]
    authority = re.split(r"[/?#]", rest, maxsplit=1)[0]
    if "@" in authority:
        return authority.rpartition("@")[0]
    # `user:pa/ss@host`: what follows the colon is no port, and an `@` comes later.
    _, colon, after = authority.partition(":")
    if colon and not after.isdigit() and not authority.startswith("[") and "@" in rest:
        return rest.split("@", 1)[0]
    return ""


def _embedded_credentials(value: str) -> list[str]:
    """The secrets written inside a connection string or URL: the `user:password` of a URL
    (the pair, so a password too short to blank alone is still blanked where the URL is
    echoed, and the password alone, for an error that prints only it), a token in the
    user-name place, and `password=...`-style parts."""
    found: list[str] = []
    for match in _URL_IN_TEXT.finditer(value):
        url = match.group()
        userinfo = _userinfo(url)
        user, has_password, password = userinfo.partition(":")
        if has_password and password:
            found += _with_decoded(userinfo) + _with_decoded(password)
            if len(userinfo) < MIN_VALUE:
                found.append(url[: url.index("://") + 3] + userinfo + "@")
        elif user and _looks_like_token(unquote(user)):
            found += _with_decoded(user)
    for name, raw in _NAMED_PART.findall(value):
        if _names_a_credential_part(name):
            found += _part_value(raw)
    if ";" in value:
        for name, raw in _ADO_PART.findall(value):
            if _names_a_credential_part(name):
                found += _part_value(raw)
    return found


def _sent_args(args: list[str]) -> list[str]:
    """Each argument's embedded credentials, and the argument after a flag such as
    `--password` or `--api-token`, which is the credential itself."""
    found: list[str] = []
    for i, arg in enumerate(args):
        found += _embedded_credentials(arg)
        flag = _FLAG.fullmatch(arg)
        if flag and i + 1 < len(args) and _names_a_credential_part(flag.group(1)):
            found += _part_value(args[i + 1])
    return found


def _blank_credentials(config: MCPConfig) -> None:
    """Have every redactor blank the credentials `config` is connected with, typed into the
    connector or picked from Settings > Secrets, including a password written inside a
    connection string. Called wherever the plaintext is produced for connecting: at startup
    and when one connector is (re)connected."""
    fields = cast(dict[str, Any], config)
    sent: list[str] = []
    for field in ("env", "headers"):
        for name, value in (fields.get(field) or {}).items():
            if not isinstance(value, str):
                continue
            if _is_credential(name, value):
                sent.append(value)
            sent += _embedded_credentials(value)
    args = fields.get("args") or []
    sent += _sent_args([arg for arg in args if isinstance(arg, str)])
    if isinstance(url := fields.get("server_url"), str):
        sent += _embedded_credentials(url)
    SecretStore.blank_also(f"mcp:{config['name']}", sent)


def with_interpreter(config: MCPConfig, state_dir: Path | None) -> MCPConfig:
    """`config` with a bare `python` command pointed at a Python that runs;
    the saved connector keeps the name it was added with."""
    command = config.get("command")
    if not command:
        return config
    resolved = resolve_python_command(command, state_dir)
    if resolved == command:
        return config
    logger.info("Connector command %s resolved to %s", command, resolved)
    return cast(MCPConfig, {**config, "command": resolved})


def _substitute_secrets(
    connector: str, field: str, value: str, host: str | None, state_dir: Path | None
) -> str:
    names = placeholders_in(value)
    if not names:
        return value
    if state_dir is None:
        raise SecretError(
            f"{connector}: {field} uses a secret, but there is nowhere to look it up."
        )
    store = SecretStore(state_dir)
    values: dict[str, str] = {}
    for name in sorted(names):
        hosts = store.hosts_of(name)
        if hosts is None:
            raise SecretError(f"{connector}: there is no secret named {name}.")
        if host is not None and not any(host_allowed(pattern, host) for pattern in hosts):
            raise SecretError(
                f"{connector}: the secret {name} may only be sent to "
                f"{', '.join(hosts)}, not {host}."
            )
        values[name] = store.resolve(name)
    return substitute(value, values)


def secret_names_used(entry: dict[str, Any]) -> set[str]:
    """The secrets a stored connector entry refers to, for refusing to delete
    one that is in use."""
    names: set[str] = set()
    for field in ("env", "headers"):
        for value in (entry.get(field) or {}).values():
            if isinstance(value, str):
                names |= placeholders_in(value)
    return names


def _read_back(stored: Any, strict: bool) -> str:
    """A stored value read back from the keychain. When the connector is only
    being listed (`strict` false) a value that can't be read is shown as empty,
    so the connector stays in the list and can be removed."""
    try:
        return resolve_secret(stored) or ""
    except RuntimeError:
        if strict:
            raise
        return ""


def load_mcp_server_configs(
    config_path: Path, state_dir: Path | None = None, *, fill_secrets: bool = True
) -> dict[str, MCPConfig]:
    """Parse a Claude-Desktop-style {"mcpServers": {name: {...}}} JSON file into
    validated MCPConfig dicts, keyed by server name (`fill_secrets=False` keeps
    `{{secret:NAME}}` placeholders as written, for showing a connector). Each `env`/`headers`
    value is resolved via runtime/secrets.py's resolve_secret before being
    returned (not inside validate_mcp_config itself, since that function is
    also called directly on live, already-plaintext request payloads in
    web/app.py's add_mcp_server, where nothing needs resolving) -- so every
    caller here keeps getting a plain string regardless of whether it's
    stored on disk as a keyring reference or (legacy, or keyring
    unavailable) plaintext."""
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    servers = raw.get("mcpServers")
    if not isinstance(servers, dict):
        raise ValueError(f'{config_path}: expected a top-level "mcpServers" object')
    result: dict[str, MCPConfig] = {}
    for name, entry in servers.items():
        config = validate_mcp_config({"type": "mcp", "name": name, **entry})
        try:
            if "env" in config:
                config["env"] = {k: _read_back(v, fill_secrets) for k, v in config["env"].items()}
            if "headers" in config:
                config["headers"] = {
                    k: _read_back(v, fill_secrets) for k, v in config["headers"].items()
                }
            if fill_secrets:
                ready = with_secrets(config, state_dir)
                _blank_credentials(ready)
                result[name] = with_interpreter(ready, state_dir)
            else:
                result[name] = config
        except (SecretError, RuntimeError) as exc:
            # One connector's missing or unreadable secret (a keychain entry
            # that is gone, or a keychain that is locked) must not take the
            # others down, or the server's start.
            logger.warning("Skipping connector %s: %s", name, exc)
    return result
