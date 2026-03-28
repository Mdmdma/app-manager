"""Unit tests for jam.kb_client — kb knowledge-base API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, call

import httpx
import pytest

from jam.config import Settings
from jam.kb_client import (
    ingest_url,
    ingest_text,
    list_namespace_documents,
    search_documents,
    _ensure_namespace,
    _JOB_APPS_NS,
)


# ── _ensure_namespace ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ensure_namespace_exists():
    """If namespace already exists (200), no POST is made."""
    client = AsyncMock()
    client.get.return_value = AsyncMock(status_code=200)

    await _ensure_namespace("http://kb:8000/api/v1", client)

    client.get.assert_called_once_with(f"http://kb:8000/api/v1/namespaces/{_JOB_APPS_NS}")
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_namespace_creates():
    """If namespace doesn't exist (404), a POST creates it."""
    client = AsyncMock()
    client.get.return_value = AsyncMock(status_code=404)
    client.post.return_value = AsyncMock(status_code=201)

    await _ensure_namespace("http://kb:8000/api/v1", client)

    client.post.assert_called_once()
    post_args = client.post.call_args
    assert _JOB_APPS_NS in post_args[1]["json"]["id"]


# ── ingest_url ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_url_success():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    ingest_response = {"nodes_ingested": 5, "documents": [{"doc_id": "abc"}]}

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        # First call: GET namespace (exists)
        ns_resp = MagicMock(status_code=200)
        # Second call: POST ingest
        ingest_resp = MagicMock(status_code=200)
        ingest_resp.raise_for_status = lambda: None
        ingest_resp.json.return_value = ingest_response

        instance.get.return_value = ns_resp
        instance.post.return_value = ingest_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ingest_url("https://example.com/job", settings)

    assert result == ingest_response
    instance.post.assert_called_once()
    post_args = instance.post.call_args
    assert post_args[1]["json"]["sources"] == ["https://example.com/job"]
    assert post_args[1]["json"]["namespace_ids"] == [_JOB_APPS_NS]


@pytest.mark.asyncio
async def test_ingest_url_creates_namespace_then_ingests():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        # GET namespace returns 404
        instance.get.return_value = MagicMock(status_code=404)
        # POST calls: first creates namespace, second ingests
        ns_create_resp = MagicMock(status_code=201)
        ingest_resp = MagicMock(status_code=200)
        ingest_resp.raise_for_status = lambda: None
        ingest_resp.json.return_value = {"nodes_ingested": 3, "documents": []}
        instance.post.side_effect = [ns_create_resp, ingest_resp]
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ingest_url("https://example.com/job", settings)

    assert result["nodes_ingested"] == 3
    assert instance.post.call_count == 2


@pytest.mark.asyncio
async def test_ingest_url_http_error():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = MagicMock(status_code=200)
        error_resp = MagicMock(status_code=500)
        error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=httpx.Request("POST", "http://x"), response=httpx.Response(500)
        )
        instance.post.return_value = error_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        with pytest.raises(httpx.HTTPStatusError):
            await ingest_url("https://example.com/job", settings)


@pytest.mark.asyncio
async def test_ingest_url_default_settings(monkeypatch):
    """Uses default kb_api_url when no settings provided."""
    monkeypatch.delenv("JAM_KB_API_URL", raising=False)

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = MagicMock(status_code=200)
        ingest_resp = MagicMock(status_code=200)
        ingest_resp.raise_for_status = lambda: None
        ingest_resp.json.return_value = {"nodes_ingested": 1, "documents": []}
        instance.post.return_value = ingest_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ingest_url("https://example.com/job")

    assert result["nodes_ingested"] == 1
    # Verify it used the default URL
    get_call = instance.get.call_args[0][0]
    assert "localhost:8000" in get_call


# ── ingest_text ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_text_success():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    text = "Software Engineer role at ACME Corp"
    url = "https://example.com/job.pdf"
    
    upload_response = {
        "batch_id": "batch-123",
        "items": [
            {"upload_id": "upload-456", "filename": "job.pdf"}
        ]
    }
    confirm_response = {
        "documents": [{"doc_id": "doc-789"}],
        "errors": []
    }

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        # First: GET namespace (exists)
        ns_resp = MagicMock(status_code=200)
        # Second: POST upload-batch
        upload_resp = MagicMock(status_code=200)
        upload_resp.raise_for_status = lambda: None
        upload_resp.json.return_value = upload_response
        # Third: POST confirm-batch
        confirm_resp = MagicMock(status_code=200)
        confirm_resp.raise_for_status = lambda: None
        confirm_resp.json.return_value = confirm_response

        instance.get.return_value = ns_resp
        instance.post.side_effect = [upload_resp, confirm_resp]
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ingest_text(text, url, settings)

    assert result == confirm_response
    # Verify upload-batch was called with correct parameters
    upload_call = instance.post.call_args_list[0]
    assert "upload-batch" in upload_call[0][0]
    # Verify confirm-batch was called
    confirm_call = instance.post.call_args_list[1]
    assert "confirm-batch" in confirm_call[0][0]
    assert confirm_call[1]["json"]["items"][0]["upload_id"] == "upload-456"


@pytest.mark.asyncio
async def test_ingest_text_empty_items():
    """When batch has no items, ingest_text returns empty response."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    text = "Some text"
    url = "https://example.com/doc.txt"
    
    upload_response = {"batch_id": "batch-123", "items": []}

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        ns_resp = MagicMock(status_code=200)
        upload_resp = MagicMock(status_code=200)
        upload_resp.raise_for_status = lambda: None
        upload_resp.json.return_value = upload_response

        instance.get.return_value = ns_resp
        instance.post.return_value = upload_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ingest_text(text, url, settings)

    assert result == {"documents": [], "errors": []}
    # Confirm-batch should NOT be called when items is empty
    assert instance.post.call_count == 1


@pytest.mark.asyncio
async def test_ingest_text_derives_filename_from_url():
    """ingest_text should extract filename from URL path."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    text = "Job posting PDF"
    url = "https://example.com/postings/job-123.pdf"
    
    upload_response = {
        "batch_id": "batch-123",
        "items": [{"upload_id": "upload-456"}]
    }
    confirm_response = {"documents": [], "errors": []}

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        ns_resp = MagicMock(status_code=200)
        upload_resp = MagicMock(status_code=200)
        upload_resp.raise_for_status = lambda: None
        upload_resp.json.return_value = upload_response
        confirm_resp = MagicMock(status_code=200)
        confirm_resp.raise_for_status = lambda: None
        confirm_resp.json.return_value = confirm_response

        instance.get.return_value = ns_resp
        instance.post.side_effect = [upload_resp, confirm_resp]
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ingest_text(text, url, settings)

    # Check that upload-batch was called with the extracted filename
    upload_call = instance.post.call_args_list[0]
    # The filename should be "job-123.pdf"
    assert "job-123.pdf" in str(upload_call)


@pytest.mark.asyncio
async def test_ingest_text_http_error():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = MagicMock(status_code=200)
        error_resp = MagicMock(status_code=500)
        error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=httpx.Request("POST", "http://x"), response=httpx.Response(500)
        )
        instance.post.return_value = error_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        with pytest.raises(httpx.HTTPStatusError):
            await ingest_text("text content", "https://example.com/doc.pdf", settings)


# ── search_documents ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_documents_success():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    search_response = {"results": [{"content": "Python engineer role", "source": "http://example.com"}]}

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        resp = MagicMock(status_code=200)
        resp.raise_for_status = lambda: None
        resp.json.return_value = search_response
        instance.post.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await search_documents("Python engineer", n_results=3, settings=settings)

    assert result == search_response["results"]
    instance.post.assert_called_once()
    call_args = instance.post.call_args
    assert "/search" in call_args[0][0]
    assert call_args[1]["json"]["query"] == "Python engineer"
    assert call_args[1]["json"]["top_k"] == 3


@pytest.mark.asyncio
async def test_search_documents_with_namespace_ids():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    search_response = {"results": [{"content": "doc1"}]}

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        resp = MagicMock(status_code=200)
        resp.raise_for_status = lambda: None
        resp.json.return_value = search_response
        instance.post.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await search_documents(
            "query", namespace_ids=["ns-a", "ns-b"], settings=settings
        )

    assert result == [{"content": "doc1"}]
    body = instance.post.call_args[1]["json"]
    assert body["namespace_ids"] == ["ns-a", "ns-b"]


@pytest.mark.asyncio
async def test_search_documents_no_namespace_ids_omits_key():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        resp = MagicMock(status_code=200)
        resp.raise_for_status = lambda: None
        resp.json.return_value = {"results": []}
        instance.post.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        await search_documents("query", settings=settings)

    body = instance.post.call_args[1]["json"]
    assert "namespace_ids" not in body


@pytest.mark.asyncio
async def test_search_documents_404_degrades_gracefully():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        resp = MagicMock(status_code=404)
        instance.post.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await search_documents("query", settings=settings)

    assert result == []


@pytest.mark.asyncio
async def test_search_documents_bare_list_response():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    bare_list = [{"content": "doc1"}, {"content": "doc2"}]

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        resp = MagicMock(status_code=200)
        resp.raise_for_status = lambda: None
        resp.json.return_value = bare_list
        instance.post.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await search_documents("query", settings=settings)

    assert result == bare_list


@pytest.mark.asyncio
async def test_search_documents_network_error_degrades_gracefully():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.side_effect = httpx.ConnectError("refused")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await search_documents("query", settings=settings)

    assert result == []


# ── list_namespace_documents ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_namespace_documents_success():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    docs_response = {
        "documents": [
            {"id": "d1", "title": "Doc 1", "content": "Content 1"},
            {"id": "d2", "title": "Doc 2", "content": "Content 2"},
        ],
        "total": 2,
    }

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        resp = MagicMock(status_code=200)
        resp.raise_for_status = lambda: None
        resp.json.return_value = docs_response
        instance.get.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await list_namespace_documents(["ns-a", "ns-b"], settings=settings)

    assert len(result) == 2
    assert result[0]["id"] == "d1"
    call_args = instance.get.call_args
    assert "/documents" in call_args[0][0]
    # namespace_id params should be passed for each ns
    params = call_args[1]["params"]
    ns_values = [v for k, v in params if k == "namespace_id"]
    assert "ns-a" in ns_values
    assert "ns-b" in ns_values


@pytest.mark.asyncio
async def test_list_namespace_documents_network_error():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.side_effect = httpx.ConnectError("refused")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await list_namespace_documents(["ns-a"], settings=settings)

    assert result == []


@pytest.mark.asyncio
async def test_list_namespace_documents_404():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        resp = MagicMock(status_code=404)
        instance.get.return_value = resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await list_namespace_documents(["ns-a"], settings=settings)

    assert result == []


@pytest.mark.asyncio
async def test_ingest_text_default_settings(monkeypatch):
    """Uses default kb_api_url when no settings provided."""
    monkeypatch.delenv("JAM_KB_API_URL", raising=False)
    
    upload_response = {
        "batch_id": "batch-123",
        "items": [{"upload_id": "upload-456"}]
    }
    confirm_response = {"documents": [], "errors": []}

    with patch("jam.kb_client.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = MagicMock(status_code=200)
        upload_resp = MagicMock(status_code=200)
        upload_resp.raise_for_status = lambda: None
        upload_resp.json.return_value = upload_response
        confirm_resp = MagicMock(status_code=200)
        confirm_resp.raise_for_status = lambda: None
        confirm_resp.json.return_value = confirm_response
        instance.post.side_effect = [upload_resp, confirm_resp]
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await ingest_text("text", "https://example.com/doc.txt")

    assert result == confirm_response
    # Verify it used the default URL
    get_call = instance.get.call_args[0][0]
    assert "localhost:8000" in get_call
