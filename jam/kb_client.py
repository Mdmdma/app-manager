"""Typed client for the kb knowledge-base REST API.

All communication with the knowledge base goes through this module.
"""

from __future__ import annotations

import httpx
import logging
import time

from jam.config import Settings

logger = logging.getLogger(__name__)

_JOB_APPS_NS = "job-applications"
_JOB_APPS_LABEL = "Job Applications"
_JOB_APPS_DESC = "Job postings and application materials"
_JOB_APPS_ICON = ""

# ── Shared AsyncClient singleton ─────────────────────────────────────────────

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Return the shared AsyncClient, creating it lazily on first call."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=30,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )
    return _client


async def close_client() -> None:
    """Close the shared AsyncClient and reset the singleton.

    Call this during server shutdown (e.g. FastAPI lifespan ``shutdown`` hook).
    """
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


# ── TTL cache for list_namespace_documents ───────────────────────────────────

_NS_CACHE_TTL = 60.0  # seconds

# key: tuple(sorted(namespace_ids)), value: (timestamp, results)
_ns_cache: dict[tuple, tuple[float, list[dict]]] = {}


def clear_ns_cache() -> None:
    """Manually invalidate the list_namespace_documents cache."""
    _ns_cache.clear()


# ── Internal helpers ─────────────────────────────────────────────────────────


async def _ensure_namespace(base_url: str, client: httpx.AsyncClient) -> None:
    """Create the job-applications namespace if it doesn't exist yet."""
    resp = await client.get(f"{base_url}/namespaces/{_JOB_APPS_NS}")
    if resp.status_code == 200:
        return
    await client.post(
        f"{base_url}/namespaces",
        json={
            "id": _JOB_APPS_NS,
            "label": _JOB_APPS_LABEL,
            "description": _JOB_APPS_DESC,
            "icon": _JOB_APPS_ICON,
        },
    )


# ── Public API ───────────────────────────────────────────────────────────────


async def search_documents(
    query: str,
    n_results: int = 5,
    namespace_ids: list[str] | None = None,
    settings: Settings | None = None,
) -> list[dict]:
    """Search the KB for documents relevant to *query*.

    Returns a list of result dicts, each expected to contain at minimum
    ``content`` and ``source`` keys.  Degrades gracefully to an empty list
    if the KB is unavailable or returns 404.

    *namespace_ids* filters the search to the given namespaces.  When
    ``None``, the KB searches all namespaces.
    """
    settings = settings or Settings()
    base_url = settings.kb_api_url.rstrip("/")
    body: dict = {"query": query, "top_k": n_results}
    if namespace_ids:
        body["namespace_ids"] = namespace_ids
    try:
        client = _get_client()
        resp = await client.post(f"{base_url}/search", json=body, timeout=10)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []
    if isinstance(data, list):
        return data
    return data.get("results", [])


async def list_namespace_documents(
    namespace_ids: list[str],
    settings: Settings | None = None,
) -> list[dict]:
    """Fetch all text chunks belonging to the given namespaces.

    Results are cached for ``_NS_CACHE_TTL`` seconds (60 s) per unique set of
    namespace IDs to avoid redundant KB round-trips.  Call ``clear_ns_cache()``
    to force a fresh fetch.

    Used by the generation loop for the "include entire namespaces" feature.
    Retrieves chunks via the ``POST /documents/chunks`` endpoint which scrolls
    Qdrant directly — no embedding generation required.  The endpoint returns
    chunks already sorted by ``(doc_id, chunk_index)``.

    Returns a list of chunk dicts each with a ``text`` field, compatible with
    ``_extract_kb_doc_content``.  Degrades gracefully to an empty list on errors.
    """
    # ── TTL cache check ──────────────────────────────────────────────────────
    cache_key = tuple(sorted(namespace_ids))
    cached = _ns_cache.get(cache_key)
    if cached is not None:
        ts, results = cached
        if time.monotonic() - ts < _NS_CACHE_TTL:
            return results

    settings = settings or Settings()
    base_url = settings.kb_api_url.rstrip("/")
    body: dict = {"namespace_ids": namespace_ids, "limit": 500}
    try:
        client = _get_client()
        resp = await client.post(f"{base_url}/documents/chunks", json=body, timeout=15)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("list_namespace_documents failed for %s: %s", namespace_ids, exc)
        return []

    result: list[dict] = data.get("chunks", [])

    # ── Populate cache ───────────────────────────────────────────────────────
    _ns_cache[cache_key] = (time.monotonic(), result)

    return result


async def ingest_url(url: str, settings: Settings | None = None) -> dict:
    """Ingest a URL into the kb knowledge base under the job-applications namespace.

    Returns the ingest response dict from the kb API.
    Raises httpx.HTTPStatusError on API failures.
    """
    settings = settings or Settings()
    base_url = settings.kb_api_url.rstrip("/")

    client = _get_client()
    await _ensure_namespace(base_url, client)
    resp = await client.post(
        f"{base_url}/ingest",
        json={
            "sources": [url],
            "namespace_ids": [_JOB_APPS_NS],
            "skip_enrichment": False,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


async def ingest_text(
    text: str, source_url: str, settings: Settings | None = None
) -> dict:
    """Ingest extracted text into the kb knowledge base.

    Used for PDFs and other non-HTML content where the text has already been
    extracted locally.  The two-step upload-batch / confirm-batch flow lets
    kb index the content without needing to fetch the URL itself.

    Returns the confirm-batch response dict from the kb API.
    Raises httpx.HTTPStatusError on API failures.
    """
    settings = settings or Settings()
    base_url = settings.kb_api_url.rstrip("/")

    # Derive a filename from the URL
    from urllib.parse import urlparse
    path = urlparse(source_url).path
    filename = path.rsplit("/", 1)[-1] if "/" in path else "document.txt"
    if not filename:
        filename = "document.txt"

    client = _get_client()
    await _ensure_namespace(base_url, client)

    # Step 1: Upload text
    resp = await client.post(
        f"{base_url}/ingest/upload-batch",
        data={
            "text": text,
            "text_filename": filename,
            "skip_enrichment": "false",
        },
        files=[
            ("namespace_ids", (None, _JOB_APPS_NS)),
        ],
        timeout=60,
    )
    resp.raise_for_status()
    batch = resp.json()

    # Step 2: Confirm all items
    items = [
        {
            "upload_id": item["upload_id"],
            "namespace_ids": [_JOB_APPS_NS],
        }
        for item in batch.get("items", [])
    ]
    if not items:
        return {"documents": [], "errors": []}

    resp = await client.post(
        f"{base_url}/ingest/confirm-batch",
        json={"items": items},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()
