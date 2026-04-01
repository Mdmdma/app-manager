"""Unit tests for jam.llm — LLM-based job info extraction."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from jam.config import Settings
from jam.llm import _parse_json, extract_job_info, llm_call, _api_key_for, _get_ollama_url, _get_cliproxy_url


# ── _parse_json ──────────────────────────────────────────────────────────────

def test_parse_json_plain():
    raw = '{"company": "Acme", "position": "Engineer"}'
    assert _parse_json(raw) == {"company": "Acme", "position": "Engineer"}


def test_parse_json_with_markdown_fences():
    raw = '```json\n{"company": "Acme"}\n```'
    assert _parse_json(raw) == {"company": "Acme"}


def test_parse_json_with_bare_fences():
    raw = '```\n{"company": "Acme"}\n```'
    assert _parse_json(raw) == {"company": "Acme"}


def test_parse_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        _parse_json("not json at all")


# ── _api_key_for ─────────────────────────────────────────────────────────────

def test_api_key_openai():
    s = Settings(openai_api_key="sk-test", llm_provider="openai")
    assert _api_key_for(s) == "sk-test"


def test_api_key_anthropic():
    s = Settings(anthropic_api_key="sk-ant-test", llm_provider="anthropic")
    assert _api_key_for(s) == "sk-ant-test"


def test_api_key_groq():
    s = Settings(groq_api_key="gsk-test", llm_provider="groq")
    assert _api_key_for(s) == "gsk-test"


def test_api_key_ollama():
    s = Settings(llm_provider="ollama")
    assert _api_key_for(s) == "ollama"


def test_api_key_unknown_provider():
    s = Settings(llm_provider="unknown")
    assert _api_key_for(s) == ""


# ── _get_ollama_url ──────────────────────────────────────────────────────────

def test_ollama_url_default():
    s = Settings()
    assert _get_ollama_url(s) == "http://localhost:11434/v1/chat/completions"


def test_ollama_url_trailing_slash():
    s = Settings(ollama_base_url="http://myhost:1234/")
    assert _get_ollama_url(s) == "http://myhost:1234/v1/chat/completions"


# ── extract_job_info ─────────────────────────────────────────────────────────

_SAMPLE_RESPONSE = json.dumps({
    "company": "Acme Corp",
    "position": "Software Engineer",
    "location": "Remote",
    "salary_range": "$120k-$150k",
    "requirements": "Python, FastAPI",
    "description": "Build great software.",
})


@pytest.mark.asyncio
async def test_extract_openai():
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", llm_model="gpt-4o")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": _SAMPLE_RESPONSE}}]
    }

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await extract_job_info("Some job posting text", settings)

    assert result["company"] == "Acme Corp"
    assert result["position"] == "Software Engineer"
    instance.post.assert_called_once()
    call_args = instance.post.call_args
    assert "api.openai.com" in call_args[0][0]


@pytest.mark.asyncio
async def test_extract_anthropic():
    settings = Settings(llm_provider="anthropic", anthropic_api_key="sk-ant-test", llm_model="claude-sonnet-4-6")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {
        "content": [{"text": _SAMPLE_RESPONSE}]
    }

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await extract_job_info("Some job posting text", settings)

    assert result["company"] == "Acme Corp"
    call_args = instance.post.call_args
    assert "api.anthropic.com" in call_args[0][0]


@pytest.mark.asyncio
async def test_extract_groq():
    settings = Settings(llm_provider="groq", groq_api_key="gsk-test", llm_model="llama-3.3-70b-versatile")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": _SAMPLE_RESPONSE}}]
    }

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await extract_job_info("Some job posting text", settings)

    assert result["company"] == "Acme Corp"
    call_args = instance.post.call_args
    assert "api.groq.com" in call_args[0][0]


@pytest.mark.asyncio
async def test_extract_ollama():
    settings = Settings(llm_provider="ollama", llm_model="llama3.2")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": _SAMPLE_RESPONSE}}]
    }

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await extract_job_info("Some job posting text", settings)

    assert result["company"] == "Acme Corp"
    call_args = instance.post.call_args
    assert "localhost:11434" in call_args[0][0]


# ── llm_call ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_call_openai():
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", llm_model="gpt-4o")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"choices": [{"message": {"content": "response text"}}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("system prompt", "user message", settings)

    assert result == "response text"
    call_args = instance.post.call_args
    assert "api.openai.com" in call_args[0][0]
    payload = call_args[1]["json"]
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == "system prompt"
    assert payload["messages"][1]["content"] == "user message"


@pytest.mark.asyncio
async def test_llm_call_anthropic():
    settings = Settings(llm_provider="anthropic", anthropic_api_key="sk-ant-test", llm_model="claude-sonnet-4-6")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"content": [{"text": "anthropic response"}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("sys", "usr", settings)

    assert result == "anthropic response"
    call_args = instance.post.call_args
    assert "api.anthropic.com" in call_args[0][0]


@pytest.mark.asyncio
async def test_llm_call_groq():
    settings = Settings(llm_provider="groq", groq_api_key="gsk-test", llm_model="llama3")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"choices": [{"message": {"content": "groq response"}}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("sys", "usr", settings)

    assert result == "groq response"
    call_args = instance.post.call_args
    assert "api.groq.com" in call_args[0][0]


@pytest.mark.asyncio
async def test_extract_http_error_propagates():
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", llm_model="gpt-4o")

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.side_effect = httpx.HTTPStatusError(
            "401", request=httpx.Request("POST", "http://x"), response=httpx.Response(401)
        )
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        with pytest.raises(httpx.HTTPStatusError):
            await extract_job_info("text", settings)


# ── _get_cliproxy_url ────────────────────────────────────────────────────────

def test_cliproxy_url_default():
    s = Settings()
    assert _get_cliproxy_url(s) == "http://localhost:8317/v1/chat/completions"


def test_cliproxy_url_trailing_slash():
    s = Settings(cliproxy_base_url="http://myhost:9000/")
    assert _get_cliproxy_url(s) == "http://myhost:9000/v1/chat/completions"


# ── _api_key_for (cliproxy) ───────────────────────────────────────────────────

def test_api_key_cliproxy():
    s = Settings(llm_provider="cliproxy")
    assert _api_key_for(s) == ""


# ── llm_call (cliproxy) ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_call_cliproxy_url_and_no_auth():
    settings = Settings(
        llm_provider="cliproxy",
        cliproxy_base_url="http://localhost:8317",
        llm_model="gpt-4o",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"choices": [{"message": {"content": "cliproxy response"}}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("sys", "usr", settings)

    assert result == "cliproxy response"
    call_args = instance.post.call_args
    # Dispatched to the cliproxy endpoint
    assert "localhost:8317" in call_args[0][0]
    assert "/v1/chat/completions" in call_args[0][0]
    # No Authorization header sent (empty api_key)
    headers = call_args[1]["headers"]
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_llm_call_cliproxy_custom_base_url():
    settings = Settings(
        llm_provider="cliproxy",
        cliproxy_base_url="http://proxy.internal:5000",
        llm_model="some-model",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("sys", "usr", settings)

    assert result == "ok"
    call_args = instance.post.call_args
    assert "proxy.internal:5000" in call_args[0][0]


# ── llm_call / _api_key_for override parameters ──────────────────────────────

@pytest.mark.asyncio
async def test_llm_call_with_provider_override():
    """provider= kwarg overrides settings.llm_provider; Anthropic endpoint used."""
    settings = Settings(
        llm_provider="openai",
        openai_api_key="sk-openai",
        anthropic_api_key="sk-anthropic",
        llm_model="claude-sonnet-4-6",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"content": [{"text": "anthropic response"}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("sys", "usr", settings, provider="anthropic")

    assert result == "anthropic response"
    call_args = instance.post.call_args
    assert "api.anthropic.com" in call_args[0][0]
    # OpenAI endpoint must NOT have been called
    assert "api.openai.com" not in call_args[0][0]


@pytest.mark.asyncio
async def test_llm_call_with_model_override():
    """model= kwarg overrides settings.llm_model in the request payload."""
    settings = Settings(
        llm_provider="openai",
        openai_api_key="sk-test",
        llm_model="gpt-4o",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"choices": [{"message": {"content": "mini response"}}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("sys", "usr", settings, model="gpt-4o-mini")

    assert result == "mini response"
    call_args = instance.post.call_args
    payload = call_args[1]["json"]
    assert payload["model"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_llm_call_overrides_none_uses_global():
    """Passing provider=None and model=None falls back to settings values."""
    settings = Settings(
        llm_provider="openai",
        openai_api_key="sk-test",
        llm_model="gpt-4o",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"choices": [{"message": {"content": "global response"}}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("sys", "usr", settings, provider=None, model=None)

    assert result == "global response"
    call_args = instance.post.call_args
    assert "api.openai.com" in call_args[0][0]
    payload = call_args[1]["json"]
    assert payload["model"] == "gpt-4o"


def test_api_key_for_explicit_provider():
    """_api_key_for resolves the key for the explicit provider, ignoring settings.llm_provider."""
    settings = Settings(
        llm_provider="openai",
        openai_api_key="sk-openai",
        anthropic_api_key="sk-anthropic",
    )
    assert _api_key_for(settings, "anthropic") == "sk-anthropic"
