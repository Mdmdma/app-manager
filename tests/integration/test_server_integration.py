import pytest
from httpx import ASGITransport, AsyncClient

from jam.server import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_full_page_load(client):
    """Integration: full page loads with all expected sections."""
    resp = await client.get("/api/v1/")
    assert resp.status_code == 200
    body = resp.text
    # Check all tabs are present
    assert "Dashboard" in body
    assert "Applications" in body
    assert "Settings" in body
    # Check stats section
    assert "stat-total" in body
    assert "stat-active" in body
    # Check JS is present
    assert "apiFetch" in body
    assert "switchTab" in body
