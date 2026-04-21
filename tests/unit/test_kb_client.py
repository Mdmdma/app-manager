"""Unit tests for jam.kb_client — kb knowledge-base API client."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

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
    clear_ns_cache,
    close_client,
)
import jam.kb_client as kb_client_module


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client() -> AsyncMock:
    """Return a fresh AsyncMock that behaves like an httpx.AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)


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

    instance = _make_client()
    ns_resp = MagicMock(status_code=200)
    ingest_resp = MagicMock(status_code=200)
    ingest_resp.raise_for_status = lambda: None
    ingest_resp.json.return_value = ingest_response

    instance.get.return_value = ns_resp
    instance.post.return_value = ingest_resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await ingest_url("https://example.com/job", settings)

    assert result == ingest_response
    instance.post.assert_called_once()
    post_args = instance.post.call_args
    assert post_args[1]["json"]["sources"] == ["https://example.com/job"]
    assert post_args[1]["json"]["namespace_ids"] == [_JOB_APPS_NS]


@pytest.mark.asyncio
async def test_ingest_url_uses_60s_timeout():
    """ingest_url passes timeout=60 to the POST call."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    instance.get.return_value = MagicMock(status_code=200)
    ingest_resp = MagicMock(status_code=200)
    ingest_resp.raise_for_status = lambda: None
    ingest_resp.json.return_value = {"nodes_ingested": 1, "documents": []}
    instance.post.return_value = ingest_resp

    with patch("jam.kb_client._get_client", return_value=instance):
        await ingest_url("https://example.com/job", settings)

    post_call = instance.post.call_args
    assert post_call[1].get("timeout") == 60


@pytest.mark.asyncio
async def test_ingest_url_creates_namespace_then_ingests():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    instance.get.return_value = MagicMock(status_code=404)
    ns_create_resp = MagicMock(status_code=201)
    ingest_resp = MagicMock(status_code=200)
    ingest_resp.raise_for_status = lambda: None
    ingest_resp.json.return_value = {"nodes_ingested": 3, "documents": []}
    instance.post.side_effect = [ns_create_resp, ingest_resp]

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await ingest_url("https://example.com/job", settings)

    assert result["nodes_ingested"] == 3
    assert instance.post.call_count == 2


@pytest.mark.asyncio
async def test_ingest_url_http_error():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    instance.get.return_value = MagicMock(status_code=200)
    error_resp = MagicMock(status_code=500)
    error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=httpx.Request("POST", "http://x"), response=httpx.Response(500)
    )
    instance.post.return_value = error_resp

    with patch("jam.kb_client._get_client", return_value=instance):
        with pytest.raises(httpx.HTTPStatusError):
            await ingest_url("https://example.com/job", settings)


@pytest.mark.asyncio
async def test_ingest_url_default_settings(monkeypatch):
    """Uses default kb_api_url when no settings provided."""
    monkeypatch.delenv("JAM_KB_API_URL", raising=False)

    instance = _make_client()
    instance.get.return_value = MagicMock(status_code=200)
    ingest_resp = MagicMock(status_code=200)
    ingest_resp.raise_for_status = lambda: None
    ingest_resp.json.return_value = {"nodes_ingested": 1, "documents": []}
    instance.post.return_value = ingest_resp

    with patch("jam.kb_client._get_client", return_value=instance):
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

    instance = _make_client()
    ns_resp = MagicMock(status_code=200)
    upload_resp = MagicMock(status_code=200)
    upload_resp.raise_for_status = lambda: None
    upload_resp.json.return_value = upload_response
    confirm_resp = MagicMock(status_code=200)
    confirm_resp.raise_for_status = lambda: None
    confirm_resp.json.return_value = confirm_response

    instance.get.return_value = ns_resp
    instance.post.side_effect = [upload_resp, confirm_resp]

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await ingest_text(text, url, settings)

    assert result == confirm_response
    upload_call = instance.post.call_args_list[0]
    assert "upload-batch" in upload_call[0][0]
    confirm_call = instance.post.call_args_list[1]
    assert "confirm-batch" in confirm_call[0][0]
    assert confirm_call[1]["json"]["items"][0]["upload_id"] == "upload-456"


@pytest.mark.asyncio
async def test_ingest_text_uses_60s_timeout():
    """ingest_text passes timeout=60 to POST calls."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    text = "Some text"
    url = "https://example.com/job.pdf"

    upload_response = {
        "batch_id": "batch-123",
        "items": [{"upload_id": "upload-456"}]
    }
    confirm_response = {"documents": [], "errors": []}

    instance = _make_client()
    instance.get.return_value = MagicMock(status_code=200)
    upload_resp = MagicMock(status_code=200)
    upload_resp.raise_for_status = lambda: None
    upload_resp.json.return_value = upload_response
    confirm_resp = MagicMock(status_code=200)
    confirm_resp.raise_for_status = lambda: None
    confirm_resp.json.return_value = confirm_response
    instance.post.side_effect = [upload_resp, confirm_resp]

    with patch("jam.kb_client._get_client", return_value=instance):
        await ingest_text(text, url, settings)

    for call in instance.post.call_args_list:
        assert call[1].get("timeout") == 60


@pytest.mark.asyncio
async def test_ingest_text_empty_items():
    """When batch has no items, ingest_text returns empty response."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    text = "Some text"
    url = "https://example.com/doc.txt"

    upload_response = {"batch_id": "batch-123", "items": []}

    instance = _make_client()
    ns_resp = MagicMock(status_code=200)
    upload_resp = MagicMock(status_code=200)
    upload_resp.raise_for_status = lambda: None
    upload_resp.json.return_value = upload_response

    instance.get.return_value = ns_resp
    instance.post.return_value = upload_resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await ingest_text(text, url, settings)

    assert result == {"documents": [], "errors": []}
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

    instance = _make_client()
    ns_resp = MagicMock(status_code=200)
    upload_resp = MagicMock(status_code=200)
    upload_resp.raise_for_status = lambda: None
    upload_resp.json.return_value = upload_response
    confirm_resp = MagicMock(status_code=200)
    confirm_resp.raise_for_status = lambda: None
    confirm_resp.json.return_value = confirm_response

    instance.get.return_value = ns_resp
    instance.post.side_effect = [upload_resp, confirm_resp]

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await ingest_text(text, url, settings)

    upload_call = instance.post.call_args_list[0]
    assert "job-123.pdf" in str(upload_call)


@pytest.mark.asyncio
async def test_ingest_text_http_error():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    instance.get.return_value = MagicMock(status_code=200)
    error_resp = MagicMock(status_code=500)
    error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=httpx.Request("POST", "http://x"), response=httpx.Response(500)
    )
    instance.post.return_value = error_resp

    with patch("jam.kb_client._get_client", return_value=instance):
        with pytest.raises(httpx.HTTPStatusError):
            await ingest_text("text content", "https://example.com/doc.pdf", settings)


@pytest.mark.asyncio
async def test_ingest_text_default_settings(monkeypatch):
    """Uses default kb_api_url when no settings provided."""
    monkeypatch.delenv("JAM_KB_API_URL", raising=False)

    upload_response = {
        "batch_id": "batch-123",
        "items": [{"upload_id": "upload-456"}]
    }
    confirm_response = {"documents": [], "errors": []}

    instance = _make_client()
    instance.get.return_value = MagicMock(status_code=200)
    upload_resp = MagicMock(status_code=200)
    upload_resp.raise_for_status = lambda: None
    upload_resp.json.return_value = upload_response
    confirm_resp = MagicMock(status_code=200)
    confirm_resp.raise_for_status = lambda: None
    confirm_resp.json.return_value = confirm_response
    instance.post.side_effect = [upload_resp, confirm_resp]

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await ingest_text("text", "https://example.com/doc.txt")

    assert result == confirm_response
    get_call = instance.get.call_args[0][0]
    assert "localhost:8000" in get_call


# ── search_documents ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_documents_success():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    search_response = {"results": [{"content": "Python engineer role", "source": "http://example.com"}]}

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = search_response
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await search_documents("Python engineer", n_results=3, settings=settings)

    assert result == search_response["results"]
    instance.post.assert_called_once()
    call_args = instance.post.call_args
    assert "/search" in call_args[0][0]
    assert call_args[1]["json"]["query"] == "Python engineer"
    assert call_args[1]["json"]["top_k"] == 3


@pytest.mark.asyncio
async def test_search_documents_uses_10s_timeout():
    """search_documents passes timeout=10 to the POST call."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"results": []}
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        await search_documents("query", settings=settings)

    post_call = instance.post.call_args
    assert post_call[1].get("timeout") == 10


@pytest.mark.asyncio
async def test_search_documents_with_namespace_ids():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    search_response = {"results": [{"content": "doc1"}]}

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = search_response
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await search_documents(
            "query", namespace_ids=["ns-a", "ns-b"], settings=settings
        )

    assert result == [{"content": "doc1"}]
    body = instance.post.call_args[1]["json"]
    assert body["namespace_ids"] == ["ns-a", "ns-b"]


@pytest.mark.asyncio
async def test_search_documents_no_namespace_ids_omits_key():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"results": []}
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        await search_documents("query", settings=settings)

    body = instance.post.call_args[1]["json"]
    assert "namespace_ids" not in body


@pytest.mark.asyncio
async def test_search_documents_404_degrades_gracefully():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    resp = MagicMock(status_code=404)
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await search_documents("query", settings=settings)

    assert result == []


@pytest.mark.asyncio
async def test_search_documents_bare_list_response():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    bare_list = [{"content": "doc1"}, {"content": "doc2"}]

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = bare_list
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await search_documents("query", settings=settings)

    assert result == bare_list


@pytest.mark.asyncio
async def test_search_documents_network_error_degrades_gracefully():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    instance.post.side_effect = httpx.ConnectError("refused")

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await search_documents("query", settings=settings)

    assert result == []


# ── list_namespace_documents ─────────────────────────────────────────────────
# Uses POST /documents/chunks (Qdrant scroll — no embedding generation).

@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure the namespace cache is clean before every test."""
    clear_ns_cache()
    yield
    clear_ns_cache()


@pytest.mark.asyncio
async def test_list_namespace_documents_uses_chunks_endpoint():
    """list_namespace_documents calls POST /documents/chunks, not POST /search."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    chunks_response = {
        "chunks": [
            {"text": "chunk 1 text", "doc_id": "d1", "chunk_index": 0},
            {"text": "chunk 2 text", "doc_id": "d1", "chunk_index": 1},
        ],
        "total": 2,
    }

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = chunks_response
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await list_namespace_documents(["ns-a", "ns-b"], settings=settings)

    instance.post.assert_called_once()
    instance.get.assert_not_called()
    call_args = instance.post.call_args
    assert "/documents/chunks" in call_args[0][0]
    body = call_args[1]["json"]
    assert body["namespace_ids"] == ["ns-a", "ns-b"]
    assert len(result) == 2
    assert result[0]["text"] == "chunk 1 text"


@pytest.mark.asyncio
async def test_list_namespace_documents_uses_15s_timeout():
    """list_namespace_documents passes timeout=15 to the POST call."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"chunks": [], "total": 0}
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        await list_namespace_documents(["ns-a"], settings=settings)

    post_call = instance.post.call_args
    assert post_call[1].get("timeout") == 15


@pytest.mark.asyncio
async def test_list_namespace_documents_server_returns_sorted_chunks():
    """Chunks are returned in the order provided by the server (sorted by doc_id + chunk_index)."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    chunks_response = {
        "chunks": [
            {"text": "first",  "doc_id": "d1", "chunk_index": 0},
            {"text": "second", "doc_id": "d1", "chunk_index": 1},
            {"text": "third",  "doc_id": "d1", "chunk_index": 2},
        ],
        "total": 3,
    }

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = chunks_response
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await list_namespace_documents(["ns-a"], settings=settings)

    texts = [r["text"] for r in result]
    assert texts == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_list_namespace_documents_network_error():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    instance.post.side_effect = httpx.ConnectError("refused")

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await list_namespace_documents(["ns-a"], settings=settings)

    assert result == []


@pytest.mark.asyncio
async def test_list_namespace_documents_404():
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    resp = MagicMock(status_code=404)
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await list_namespace_documents(["ns-a"], settings=settings)

    assert result == []


@pytest.mark.asyncio
async def test_list_namespace_documents_sends_limit_500():
    """Verify the request body sends limit=500 to the chunks endpoint."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"chunks": [], "total": 0}
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        await list_namespace_documents(["ns-a"], settings=settings)

    body = instance.post.call_args[1]["json"]
    assert body["limit"] == 500
    assert body["namespace_ids"] == ["ns-a"]
    assert "top_k" not in body
    assert "query" not in body


@pytest.mark.asyncio
async def test_list_namespace_documents_empty_namespace_ids():
    """Empty namespace_ids list should still make the API call (no early return)."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = {"chunks": [], "total": 0}
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result = await list_namespace_documents([], settings=settings)

    assert result == []


# ── TTL cache ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_namespace_documents_cache_hit_skips_request():
    """Second call with same namespaces within TTL returns cached data, no HTTP."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    chunks_response = {
        "chunks": [{"text": "chunk", "doc_id": "d1", "chunk_index": 0}],
        "total": 1,
    }

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = chunks_response
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        result1 = await list_namespace_documents(["ns-a"], settings=settings)
        result2 = await list_namespace_documents(["ns-a"], settings=settings)

    # HTTP was only called once despite two invocations
    assert instance.post.call_count == 1
    assert result1 == result2


@pytest.mark.asyncio
async def test_list_namespace_documents_cache_key_order_independent():
    """Cache key is sorted, so ['b','a'] and ['a','b'] share the same entry."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    chunks_response = {
        "chunks": [{"text": "x", "doc_id": "d1", "chunk_index": 0}],
        "total": 1,
    }

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = chunks_response
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        await list_namespace_documents(["ns-b", "ns-a"], settings=settings)
        await list_namespace_documents(["ns-a", "ns-b"], settings=settings)

    assert instance.post.call_count == 1


@pytest.mark.asyncio
async def test_list_namespace_documents_cache_expires_after_ttl():
    """After TTL elapses the cache is stale and a new HTTP call is made."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    chunks_response = {"chunks": [], "total": 0}

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = chunks_response
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        # First call — populates cache
        await list_namespace_documents(["ns-a"], settings=settings)

        # Manually expire the cache entry by backdating the timestamp
        key = ("ns-a",)
        ts, data = kb_client_module._ns_cache[key]
        kb_client_module._ns_cache[key] = (ts - kb_client_module._NS_CACHE_TTL - 1, data)

        # Second call — cache is stale, should hit HTTP again
        await list_namespace_documents(["ns-a"], settings=settings)

    assert instance.post.call_count == 2


@pytest.mark.asyncio
async def test_clear_ns_cache_forces_fresh_request():
    """clear_ns_cache() causes the next call to bypass the cache."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")
    chunks_response = {"chunks": [], "total": 0}

    instance = _make_client()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json.return_value = chunks_response
    instance.post.return_value = resp

    with patch("jam.kb_client._get_client", return_value=instance):
        await list_namespace_documents(["ns-a"], settings=settings)
        clear_ns_cache()
        await list_namespace_documents(["ns-a"], settings=settings)

    assert instance.post.call_count == 2


@pytest.mark.asyncio
async def test_list_namespace_documents_error_does_not_populate_cache():
    """A failed request must not store anything in the cache."""
    settings = Settings(kb_api_url="http://kb:8000/api/v1")

    instance = _make_client()
    instance.post.side_effect = httpx.ConnectError("refused")

    with patch("jam.kb_client._get_client", return_value=instance):
        await list_namespace_documents(["ns-a"], settings=settings)
        # Second call must still hit the network
        instance.post.side_effect = httpx.ConnectError("refused")
        await list_namespace_documents(["ns-a"], settings=settings)

    assert instance.post.call_count == 2


# ── close_client ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_close_client_resets_singleton():
    """close_client() closes the shared client and resets the module-level var."""
    # Force a client to exist
    client = kb_client_module._get_client()
    assert kb_client_module._client is not None

    await close_client()

    assert kb_client_module._client is None


@pytest.mark.asyncio
async def test_close_client_idempotent():
    """Calling close_client() when _client is None must not raise."""
    kb_client_module._client = None
    await close_client()  # should not raise


@pytest.mark.asyncio
async def test_get_client_recreates_after_close():
    """After close_client(), _get_client() returns a new open client."""
    await close_client()
    client = kb_client_module._get_client()
    assert client is not None
    assert not client.is_closed
    # Clean up
    await close_client()


# ── _get_client singleton ─────────────────────────────────────────────────────

def test_get_client_returns_same_instance():
    """_get_client() returns the same object on repeated calls."""
    # Ensure clean state
    kb_client_module._client = None
    try:
        c1 = kb_client_module._get_client()
        c2 = kb_client_module._get_client()
        assert c1 is c2
    finally:
        # We can't await here in a sync test, so just reset the module var
        kb_client_module._client = None
