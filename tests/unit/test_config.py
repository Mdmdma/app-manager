import os

from jam.config import Settings


def test_defaults():
    """Settings should have sensible defaults without any env vars."""
    s = Settings()
    assert s.kb_api_url == "http://localhost:8000/api/v1"
    assert s.port == 8001


def test_env_overrides(monkeypatch):
    """Settings should read from JAM_* environment variables."""
    monkeypatch.setenv("JAM_KB_API_URL", "http://kb:9000/api/v1")
    monkeypatch.setenv("JAM_PORT", "9999")
    s = Settings()
    assert s.kb_api_url == "http://kb:9000/api/v1"
    assert s.port == 9999
