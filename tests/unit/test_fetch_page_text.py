"""Unit tests for _fetch_page_text — content-type dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from jam.server import _fetch_page_text


def _mock_response(*, content_type: str, text: str = "", content: bytes = b""):
    """Build a fake httpx.Response with the given content type."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = lambda: None
    resp.headers = {"content-type": content_type}
    resp.text = text
    resp.content = content
    return resp


@pytest.mark.asyncio
async def test_html_strips_tags():
    html = "<html><head><script>x</script></head><body><p>Hello World</p></body></html>"
    resp = _mock_response(content_type="text/html", text=html)

    with patch("jam.server.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        text, kind = await _fetch_page_text("https://example.com/job")

    assert "Hello World" in text
    assert "<p>" not in text
    assert "<script>" not in text
    assert kind == "html"


@pytest.mark.asyncio
async def test_plain_text():
    resp = _mock_response(content_type="text/plain", text="Software Engineer at Acme Corp")

    with patch("jam.server.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        text, kind = await _fetch_page_text("https://example.com/job.txt")

    assert text == "Software Engineer at Acme Corp"
    assert kind == "text"


@pytest.mark.asyncio
async def test_pdf_content_type():
    fake_text = "Software Engineer Role"

    mock_page = MagicMock()
    mock_page.get_text.return_value = fake_text
    mock_doc = MagicMock()
    mock_doc.__iter__ = lambda self: iter([mock_page])
    mock_doc.close = MagicMock()

    resp = _mock_response(content_type="application/pdf", content=b"%PDF-fake")

    with patch("jam.server.httpx.AsyncClient") as MockClient, \
         patch("fitz.open", return_value=mock_doc) as mock_fitz:
        instance = AsyncMock()
        instance.get.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        text, kind = await _fetch_page_text("https://example.com/posting.pdf")

    assert "Software Engineer Role" in text
    assert kind == "pdf"
    mock_fitz.assert_called_once_with(stream=b"%PDF-fake", filetype="pdf")
    mock_doc.close.assert_called_once()


@pytest.mark.asyncio
async def test_pdf_detected_by_url_extension():
    """Even if content-type is octet-stream, .pdf extension triggers PDF path."""
    fake_text = "Data Analyst Position"
    mock_page = MagicMock()
    mock_page.get_text.return_value = fake_text
    mock_doc = MagicMock()
    mock_doc.__iter__ = lambda self: iter([mock_page])
    mock_doc.close = MagicMock()

    resp = _mock_response(content_type="application/octet-stream", content=b"%PDF-fake")

    with patch("jam.server.httpx.AsyncClient") as MockClient, \
         patch("fitz.open", return_value=mock_doc):
        instance = AsyncMock()
        instance.get.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        text, kind = await _fetch_page_text("https://example.com/job.PDF")

    assert "Data Analyst Position" in text
    assert kind == "pdf"


@pytest.mark.asyncio
async def test_pdf_multi_page():
    pages = [MagicMock(), MagicMock()]
    pages[0].get_text.return_value = "Page one text"
    pages[1].get_text.return_value = "Page two text"
    mock_doc = MagicMock()
    mock_doc.__iter__ = lambda self: iter(pages)
    mock_doc.close = MagicMock()

    resp = _mock_response(content_type="application/pdf", content=b"%PDF-fake")

    with patch("jam.server.httpx.AsyncClient") as MockClient, \
         patch("fitz.open", return_value=mock_doc):
        instance = AsyncMock()
        instance.get.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        text, kind = await _fetch_page_text("https://example.com/posting.pdf")

    assert "Page one text" in text
    assert "Page two text" in text
    assert kind == "pdf"
