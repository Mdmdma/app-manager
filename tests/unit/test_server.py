import pytest
from httpx import ASGITransport, AsyncClient

from jam.server import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_index_returns_html(client):
    """GET / should return the HTML page."""
    resp = await client.get("/api/v1/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Job Application Manager" in resp.text


@pytest.mark.asyncio
async def test_health(client):
    """GET /health should return ok status."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
