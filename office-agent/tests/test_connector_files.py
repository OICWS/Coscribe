"""Connector output delivery using the same result shapes as the MCP adapter."""

import json
import logging

import httpx
import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import StructuredTool

from coscribe.conversation import connector_files
from coscribe.conversation.activity import summarize_activity
from coscribe.conversation.connector_files import ConnectorFiles, DownloadError
from coscribe.runtime import tool_metadata
from coscribe.tools import WorkspaceScope

URL = "https://files.example.com/export?X-Amz-Signature=private"
PDF = b"%PDF-1.7\noriginal text layer\n%%EOF\n"


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    scope = WorkspaceScope(tmp_path / "workspace")
    downloads = ConnectorFiles(tmp_path / "state", "chat", lambda: scope)

    async def public_ip(host, port):
        assert port == 443
        return "192.0.2.5"

    monkeypatch.setattr(connector_files, "_public_ip", public_ip)
    return downloads, scope


def _offered(downloads):
    offered = downloads.offer_links({"urls": [URL]})
    assert URL not in repr(offered)
    return offered["urls"][0]["file_ref"]


@pytest.mark.asyncio
async def test_connector_result_raw_pdf_and_output_card(delivery, monkeypatch, caplog):
    downloads, scope = delivery

    async def export() -> tuple[list, dict]:
        content = [{"type": "text", "text": json.dumps({"urls": [URL]})}]
        artifact = {"structured_content": {"download_url": URL}}
        return content, artifact

    remote = StructuredTool.from_function(
        coroutine=export,
        name="canva_export",
        description="Export",
        response_format="content_and_artifact",
    )
    tool_metadata(remote, risk_category="EXTERNAL", category="mcp:canva")
    wrapped = downloads.wrap(remote)
    result = await wrapped.ainvoke(
        {"type": "tool_call", "name": "canva_export", "id": "1", "args": {}}
    )
    ref = json.loads(result.content[0]["text"])["urls"][0]["file_ref"]
    assert ref == result.artifact["structured_content"]["download_url"]["file_ref"]
    assert URL not in repr(result)

    async def request(transport, request):
        assert request.url.host == "192.0.2.5"
        assert request.url.query == b"X-Amz-Signature=private"
        assert request.headers["host"] == "files.example.com"
        assert request.extensions["sni_hostname"] == "files.example.com"
        assert "authorization" not in request.headers
        return httpx.Response(
            200,
            stream=httpx.ByteStream(PDF),
            headers={
                "content-type": "application/pdf",
                "content-disposition": "inline; filename*=UTF-8''original%20file.pdf",
            },
        )

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", request)
    save = downloads.tool()
    first = await save(ref)
    assert (scope.root / "downloads/original file.pdf").read_bytes() == PDF
    assert json.loads(await save(ref))["files_written"] == ["downloads/original file (2).pdf"]
    assert "private" not in caplog.text
    report = summarize_activity(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "save_connector_file", "args": {"file_ref": ref}, "id": "saved"}
                ],
            ),
            ToolMessage(first, tool_call_id="saved"),
        ],
        {},
        scope,
    )
    assert report["outputs"][0]["connector_download"]
    assert report["outputs"][0]["path"] == "downloads/original file.pdf"


@pytest.mark.asyncio
async def test_structured_only_resource_and_expired_reference(delivery, monkeypatch):
    downloads, scope = delivery
    content, artifact = downloads.offer_links(([], {"structured_content": {"downloadUrl": URL}}))
    ref = artifact["structured_content"]["downloadUrl"]["file_ref"]
    assert ref in repr(content)
    resource = [{"type": "file", "url": URL, "mime_type": "application/pdf"}]
    content = downloads.offer_links(resource)
    assert content[0]["type"] == "text" and URL not in repr(content)
    assert downloads.offer_links("See https://example.com/docs") == "See https://example.com/docs"

    monkeypatch.setattr(connector_files.time, "monotonic", lambda: 10**12)
    with pytest.raises(DownloadError, match="expired"):
        await downloads.tool()(ref)
    assert not (scope.root / "downloads").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["expired", "html", "interrupted", "oversized", "redirect"])
async def test_failed_download_does_not_leave_files(delivery, monkeypatch, failure):
    downloads, scope = delivery

    class Interrupted(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield PDF * 4000
            raise httpx.ReadError(URL)

    async def request(transport, request):
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://unlisted.example.org/final"})
        if failure == "expired":
            return httpx.Response(403)
        if failure == "html":
            return httpx.Response(200, headers={"content-type": "text/html"}, content=b"Login")
        if failure == "oversized":
            return httpx.Response(200, headers={"content-length": "104857601"}, content=PDF)
        return httpx.Response(200, stream=Interrupted())

    def check_url(url):
        if url != URL:
            raise PermissionError("Domain blocked")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", request)
    monkeypatch.setattr(downloads._network, "check_url", check_url)
    with pytest.raises((DownloadError, PermissionError)) as error:
        await downloads.tool()(_offered(downloads))
    assert URL not in str(error.value)
    assert list((scope.root / "downloads").glob("*")) == []
