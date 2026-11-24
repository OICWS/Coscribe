"""Save HTTPS file links returned by MCP without giving the model the download URL."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import mimetypes
import os
import re
import secrets
import socket
import tempfile
import time
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from email.message import Message
from functools import wraps
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import parse_qsl, unquote, urlsplit

import httpx
from langchain_core.tools import BaseTool

from ..runtime import NetworkGuard, ToolMetadata, tool_metadata
from ..tools import WorkspaceScope, connector_of
from .capability_guard import TurnedOff, capability_refusal

_MAX_BYTES = 100 * 1024 * 1024
_TTL = 15 * 60
_MAX_OFFERS = 128
_MAX_REDIRECTS = 5
_DOWNLOAD_KEYS = frozenset({"downloadurl", "downloadurls", "exporturl", "exporturls"})
_SIGNED_KEYS = frozenset(
    {
        "x-amz-signature",
        "x-goog-signature",
        "signature",
        "sig",
        "token",
        "access_token",
    }
)
_FILE_EXTENSIONS = {
    ".pdf",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".csv",
    ".tsv",
    ".mp3",
    ".mp4",
    ".wav",
}
_URL_IN_TEXT = re.compile(r"""https?://[^\s<>"'\\]+""", re.IGNORECASE)
_fetching_connector_headers: ContextVar[bool] = ContextVar(
    "fetching_connector_headers", default=False
)

# HTTP Core prints response headers at DEBUG, including signed Location headers. Keep
# tracing for other requests and leave errors from file delivery to the caller below.
logging.getLogger("httpcore.http11").addFilter(lambda _: not _fetching_connector_headers.get())


class DownloadError(ValueError):
    """A file delivery error safe to show in the conversation."""


@dataclass
class _Offer:
    url: str
    root: Path
    expires: float


def _file_name(value: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", PureWindowsPath(value).name)
    name = name.strip(" .")[:160].rstrip(" .")
    return name if name and not PureWindowsPath(name).is_reserved() else "connector-download"


def _url_name(url: str) -> str:
    return _file_name(unquote(urlsplit(url).path.rsplit("/", 1)[-1]))


def _signed(url: str) -> bool:
    return any(key.lower() in _SIGNED_KEYS for key, _ in parse_qsl(urlsplit(url).query))


def _name_from_response(response: httpx.Response, offer: _Offer) -> str:
    disposition = Message()
    disposition["content-disposition"] = response.headers.get("content-disposition", "")
    name = _file_name(disposition.get_filename() or _url_name(offer.url))
    if not Path(name).suffix:
        media_type = response.headers.get("content-type", "").partition(";")[0].strip().lower()
        name += mimetypes.guess_extension(media_type) or ""
    return name


async def _public_ip(host: str, port: int) -> str:
    addresses = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    for _, _, _, _, address in addresses:
        ip = ipaddress.ip_address(address[0])
        if ip.is_global and not ip.is_multicast:
            return str(ip)
    raise DownloadError("The connector file link must point to a public HTTPS address.")


def _publish(staged: Path, folder: Path, name: str) -> Path:
    path = folder / name
    for index in range(1, 10_001):
        candidate = path if index == 1 else path.with_stem(f"{path.stem} ({index})")
        try:
            if os.name == "nt":
                staged.rename(candidate)  # Windows rename fails if the destination exists.
            else:
                os.link(staged, candidate)
        except FileExistsError:
            continue
        return candidate
    raise DownloadError("There are too many files with this name in the downloads folder.")


class _ResultLinks:
    """Share each reference between the adapter's content blocks and structured artifact."""

    def __init__(self, register: Callable[[str], dict[str, str]], export: bool) -> None:
        self.seen: dict[str, dict[str, str]] = {}
        self._register = register
        self._keys = _DOWNLOAD_KEYS | {"urls"} if export else _DOWNLOAD_KEYS

    def _offered(self, url: str) -> dict[str, str]:
        if url not in self.seen:
            self.seen[url] = self._register(url)
        return self.seen[url]

    def _is_file(self, url: str, *, explicit: bool, by_extension: bool = True) -> bool:
        try:
            parsed = urlsplit(url)
            return (
                parsed.scheme in ("http", "https")
                and bool(parsed.hostname)
                and (
                    explicit
                    or url in self.seen
                    or _signed(url)
                    or by_extension
                    and Path(parsed.path).suffix.lower() in _FILE_EXTENSIONS
                )
            )
        except ValueError:
            return False

    def _in_text(self, match: re.Match[str]) -> str:
        raw = match[0]
        url = raw.rstrip(")]},.;")
        if not self._is_file(url, explicit=False, by_extension=False):
            return raw
        return json.dumps(self._offered(url), ensure_ascii=False) + raw[len(url) :]

    def _text(self, value: str, *, explicit: bool) -> Any:
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(stripped)
            except ValueError:
                pass
            else:
                replaced = self.replace(parsed, explicit=explicit)
                return json.dumps(replaced, ensure_ascii=False) if replaced != parsed else value
        if _URL_IN_TEXT.fullmatch(stripped) and self._is_file(stripped, explicit=explicit):
            return self._offered(stripped)
        return _URL_IN_TEXT.sub(self._in_text, value)

    def _mapping(self, value: dict[str, Any], *, explicit: bool) -> dict[str, Any]:
        if value.get("type") in ("file", "image") and isinstance(url := value.get("url"), str):
            if self._is_file(url, explicit=True):
                return {"type": "text", "text": json.dumps(self._offered(url), ensure_ascii=False)}
        transformed = {}
        for key, item in value.items():
            normalized = key.lower().replace("_", "").replace("-", "")
            download_field = normalized in self._keys or (key in ("url", "href") and explicit)
            replaced = self.replace(item, explicit=download_field)
            if key == "text" and isinstance(replaced, dict):
                replaced = json.dumps(replaced, ensure_ascii=False)
            transformed[key] = replaced
        return transformed

    def replace(self, value: Any, *, explicit: bool = False) -> Any:
        if isinstance(value, str):
            return self._text(value, explicit=explicit)
        if isinstance(value, list):
            return [self.replace(item, explicit=explicit) for item in value]
        if isinstance(value, dict):
            return self._mapping(value, explicit=explicit)
        return value


class ConnectorFiles:
    def __init__(
        self, state_dir: Path, thread_id: str, scope: Callable[[], WorkspaceScope]
    ) -> None:
        self._state_dir = state_dir
        self._scope = scope
        self._network = NetworkGuard(state_dir, thread_id)
        self._offers: dict[str, _Offer] = {}

    def wrap(self, tool: Any) -> Any:
        if not isinstance(tool, BaseTool) or not connector_of(tool):
            return tool
        original = getattr(tool, "coroutine", None)
        if original is None:
            return tool

        @wraps(original)
        async def deliver(*args: Any, **kwargs: Any) -> Any:
            return self.offer_links(
                await original(*args, **kwargs),
                export=any(word in tool.name.lower() for word in ("download", "export")),
            )

        return tool.model_copy(update={"coroutine": deliver})

    def _register(self, url: str, now: float) -> dict[str, str]:
        if len(self._offers) >= _MAX_OFFERS:
            del self._offers[next(iter(self._offers))]
        ref = secrets.token_urlsafe(18)
        self._offers[ref] = _Offer(url, self._scope().root, now + _TTL)
        name = _url_name(url)
        if _signed(url):
            suffix = Path(name).suffix.lower()
            name = "connector-download" + (suffix if suffix in _FILE_EXTENSIONS else "")
        return {"file_ref": ref, "name": name, "save_with": "save_connector_file"}

    def offer_links(self, result: Any, *, export: bool = False) -> Any:
        """Replace recognizable file links before the model and transcript see the tool result."""
        now = time.monotonic()
        self._offers = {ref: item for ref, item in self._offers.items() if item.expires > now}
        links = _ResultLinks(lambda url: self._register(url, now), export)
        if not isinstance(result, tuple) or len(result) != 2:
            return links.replace(result)
        content, artifact = result
        content = links.replace(content)
        visible = set(links.seen)
        artifact = links.replace(artifact)
        extra = [item for url, item in links.seen.items() if url not in visible]
        if extra:
            blocks = (
                content if isinstance(content, list) else [{"type": "text", "text": content or ""}]
            )
            content = [*blocks, {"type": "text", "text": json.dumps(extra, ensure_ascii=False)}]
        return content, artifact

    async def _get(self, transport: httpx.AsyncHTTPTransport, url: str) -> httpx.Response:
        for _ in range(_MAX_REDIRECTS + 1):
            original = httpx.URL(url)
            if original.scheme != "https" or not original.host or original.userinfo:
                raise DownloadError(
                    "The connector file link must be HTTPS without URL credentials."
                )
            self._network.check_url(str(original))
            # Resolve each redirect and use the checked address for the connection. Keep the
            # original Host and TLS name so TLS and signed-request validation still use the URL.
            address = await _public_ip(original.host, original.port or 443)
            request = httpx.Request(
                "GET",
                original.copy_with(host=address),
                headers={"Host": original.netloc.decode(), "Accept-Encoding": "identity"},
                extensions={
                    "sni_hostname": original.raw_host.decode(),
                    "timeout": httpx.Timeout(30).as_dict(),
                },
            )
            # A normal HTTPX client logs the full request URL at INFO, including its signature.
            token = _fetching_connector_headers.set(True)
            try:
                response = await transport.handle_async_request(request)
            finally:
                _fetching_connector_headers.reset(token)
            response.request = request
            if not response.has_redirect_location:
                return response
            await response.aclose()
            url = str(original.join(response.headers["location"]))
        raise DownloadError("The connector file link redirected too many times.")

    async def _save(self, entry: _Offer, folder: Path) -> tuple[Path, int]:
        staged: Path | None = None
        try:
            async with (
                asyncio.timeout(120),
                httpx.AsyncHTTPTransport(
                    trust_env=False, limits=httpx.Limits(max_keepalive_connections=0)
                ) as transport,
            ):
                response = await self._get(transport, entry.url)
                try:
                    if response.status_code in (401, 403, 410):
                        raise DownloadError(
                            "The connector file link expired or was refused. Export the file again."
                        )
                    if response.status_code != 200:
                        raise DownloadError(
                            f"The connector file server returned HTTP {response.status_code}."
                        )
                    if response.headers.get("content-type", "").lower().startswith("text/html"):
                        raise DownloadError(
                            "The connector returned a web page. Ask it for a direct file link."
                        )
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise DownloadError(
                            "The connector server did not send the original file bytes."
                        )
                    length = response.headers.get("content-length", "")
                    if length.isdecimal() and int(length) > _MAX_BYTES:
                        raise DownloadError("The connector file is larger than 100 MiB.")
                    name = _name_from_response(response, entry)
                    folder.mkdir(exist_ok=True)
                    size = 0
                    prefix = b""
                    with tempfile.NamedTemporaryFile(
                        dir=folder, prefix=".connector-", suffix=".part", delete=False
                    ) as stream:
                        staged = Path(stream.name)
                        async for block in response.aiter_raw(chunk_size=64 * 1024):
                            size += len(block)
                            if size > _MAX_BYTES:
                                raise DownloadError("The connector file is larger than 100 MiB.")
                            if len(prefix) < 512:
                                prefix = (prefix + block)[:512]
                            stream.write(block)
                    if not size:
                        raise DownloadError("The connector returned an empty file.")
                    if name.lower().endswith(".pdf") and not prefix.startswith(b"%PDF-"):
                        raise DownloadError("The connector did not return a PDF file.")
                finally:
                    await response.aclose()
            assert staged is not None
            return _publish(staged, folder, name), size
        except (TimeoutError, httpx.TimeoutException):
            raise DownloadError("The connector file download timed out.") from None
        except (httpx.HTTPError, httpx.InvalidURL, OSError, ValueError) as exc:
            if isinstance(exc, (DownloadError, PermissionError)):
                raise
            raise DownloadError("The connector file could not be downloaded or saved.") from None
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)

    def tool(self) -> Callable[..., Any]:
        metadata = ToolMetadata(risk_category="WRITE_LOCAL", category="filesystem")

        async def save_connector_file(file_ref: str) -> str:
            """Save a file offered by a connector into the workspace, using its file_ref.
            Use this after an export or download instead of opening the link in a browser."""
            refusal = capability_refusal(
                self._state_dir, "save_connector_file", metadata, {}, self._scope
            )
            if refusal is not None:
                raise TurnedOff(refusal)
            scope = self._scope()
            entry = self._offers.get(file_ref)
            if entry is None or entry.expires <= time.monotonic() or entry.root != scope.root:
                raise DownloadError(
                    "The connector file reference expired or is unavailable. Export the file again."
                )
            folder = scope.resolve("downloads", write=True)
            if folder != scope.root / "downloads":
                raise DownloadError("The downloads folder must be inside the current workspace.")
            path, size = await self._save(entry, folder)
            return json.dumps({"files_written": [scope.relative(path)], "bytes_written": size})

        return tool_metadata(
            save_connector_file, risk_category=metadata.risk_category, category=metadata.category
        )
