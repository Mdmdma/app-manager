"""Typed client for the kb knowledge-base REST API.

All communication with the knowledge base goes through this module.
"""

from __future__ import annotations

import httpx
import logging

from jam.config import Settings

logger = logging.getLogger(__name__)

_JOB_APPS_NS = "job-applications"
_JOB_APPS_LABEL = "Job Applications"
_JOB_APPS_DESC = "Job postings and application materials"
_JOB_APPS_ICON = ""


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
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{base_url}/search", json=body)
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

    Used by the generation loop for the "include entire namespaces" feature.
    Retrieves chunks via the search endpoint (the only KB API that returns text
    content) using a broad generic query, then groups and sorts chunks by
    doc_id + chunk_index to reconstruct each document in reading order.

    Returns a list of chunk dicts each with a ``text`` field, compatible with
    ``_extract_kb_doc_content``.  Degrades gracefully to an empty list on errors.
    """
    settings = settings or Settings()
    base_url = settings.kb_api_url.rstrip("/")
    # Use a high top_k to capture all chunks across the namespaces.
    # The KB API caps top_k at 100, so we must stay within that limit.
    # A neutral single-space query minimises semantic bias without preferring
    # any particular topic or character.
    body: dict = {"query": " ", "top_k": 100, "namespace_ids": namespace_ids}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{base_url}/search", json=body)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("list_namespace_documents failed for %s: %s", namespace_ids, exc)
        return []

    raw: list[dict] = data if isinstance(data, list) else data.get("results", [])

    # Group chunks by doc_id and sort by chunk_index so the text reads in order.
    from collections import defaultdict
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for chunk in raw:
        doc_id = chunk.get("doc_id") or chunk.get("id", "")
        by_doc[doc_id].append(chunk)

    result: list[dict] = []
    for doc_id, chunks in by_doc.items():
        ordered = sorted(chunks, key=lambda c: c.get("chunk_index", 0))
        for chunk in ordered:
            result.append(chunk)

    return result


async def ingest_url(url: str, settings: Settings | None = None) -> dict:
    """Ingest a URL into the kb knowledge base under the job-applications namespace.

    Returns the ingest response dict from the kb API.
    Raises httpx.HTTPStatusError on API failures.
    """
    settings = settings or Settings()
    base_url = settings.kb_api_url.rstrip("/")

    async with httpx.AsyncClient(timeout=60) as client:
        await _ensure_namespace(base_url, client)
        resp = await client.post(
            f"{base_url}/ingest",
            json={
                "sources": [url],
                "namespace_ids": [_JOB_APPS_NS],
                "skip_enrichment": False,
            },
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

    async with httpx.AsyncClient(timeout=60) as client:
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
        )
        resp.raise_for_status()
        return resp.json()
