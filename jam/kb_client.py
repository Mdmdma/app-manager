"""Typed client for the kb knowledge-base REST API.

All communication with the knowledge base goes through this module.
"""

from __future__ import annotations

import httpx

from jam.config import Settings

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
