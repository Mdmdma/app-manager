import pytest

from jam.config import Settings


@pytest.fixture
def settings():
    """Default test settings."""
    return Settings(
        kb_api_url="http://localhost:8000/api/v1",
        port=8001,
    )
