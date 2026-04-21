"""Unit tests for jam.llm — LLM-based job info extraction."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from jam.config import Settings
from jam.llm import (
    _parse_json,
    _web_search_tool,
    _call_anthropic,
    extract_job_info,
    extract_email_info,
    llm_call,
    llm_call_with_trace,
    LLMTraceResult,
    _api_key_for,
    _get_ollama_url,
    _get_cliproxy_url,
)


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
    """Prose with no braces at all raises ValueError (not JSONDecodeError)."""
    with pytest.raises(ValueError, match="no JSON object"):
        _parse_json("not json at all")


def test_parse_json_prose_preamble():
    """Prose before the JSON object is stripped; only the object is parsed."""
    raw = 'Here is the result: {"a": 1}'
    assert _parse_json(raw) == {"a": 1}


def test_parse_json_trailing_prose():
    """Trailing text after the last closing brace is ignored."""
    raw = '{"a": 1} Here is some trailing text.'
    assert _parse_json(raw) == {"a": 1}


def test_parse_json_prose_preamble_and_trailing():
    """Both leading prose and trailing prose are stripped."""
    raw = 'Sure! Here you go:\n{"company": "X", "position": "Y"}\nHope that helps!'
    result = _parse_json(raw)
    assert result == {"company": "X", "position": "Y"}


def test_parse_json_empty_string_raises():
    with pytest.raises(ValueError, match="empty response"):
        _parse_json("")


def test_parse_json_whitespace_only_raises():
    with pytest.raises(ValueError, match="empty response"):
        _parse_json("   \n\t  ")


def test_parse_json_no_braces_raises():
    with pytest.raises(ValueError, match="no JSON object"):
        _parse_json("The model could not determine a JSON structure.")


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
        "content": [{"type": "text", "text": _SAMPLE_RESPONSE}]
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
    mock_resp.json.return_value = {"content": [{"type": "text", "text": "anthropic response"}]}

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
async def test_llm_call_cliproxy_url_and_anthropic_headers():
    """cliproxy now routes through _call_anthropic: hits /v1/messages with x-api-key."""
    settings = Settings(
        llm_provider="cliproxy",
        cliproxy_base_url="http://localhost:8317",
        llm_model="claude-opus-4-6",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"content": [{"type": "text", "text": "cliproxy response"}]}

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await llm_call("sys", "usr", settings)

    assert result == "cliproxy response"
    call_args = instance.post.call_args
    # Dispatched to the Anthropic Messages endpoint on the cliproxy host
    assert "localhost:8317" in call_args[0][0]
    assert "/v1/messages" in call_args[0][0]
    # Anthropic-style auth header used (x-api-key), not Bearer
    headers = call_args[1]["headers"]
    assert "x-api-key" in headers
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
    mock_resp.json.return_value = {"content": [{"type": "text", "text": "ok"}]}

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
    assert "/v1/messages" in call_args[0][0]


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
    mock_resp.json.return_value = {"content": [{"type": "text", "text": "anthropic response"}]}

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


# ── extract_email_info ───────────────────────────────────────────────────────

def _make_openai_mock_client(content: str):
    """Return a patched AsyncClient instance whose .post() returns the given content."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"choices": [{"message": {"content": content}}]}

    instance = AsyncMock()
    instance.post.return_value = mock_resp
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=False)
    return instance


_INTERVIEW_CONFIRMED_RESPONSE = json.dumps({
    "kind": "interview_invite",
    "confidence": "high",
    "interview": {
        "round_type": "technical",
        "scheduled_at": "2026-05-10",
        "scheduled_time": "14:00",
        "interviewer_names": "Alice, Bob",
        "location": "https://zoom.us/j/123456789",
        "prep_notes": "60-minute technical screen with coding exercise",
        "links": ["https://zoom.us/j/123456789", "https://calendar.google.com/event/abc"],
    },
    "rejection": {
        "summary": None,
        "reasons": None,
        "links": [],
    },
    "received_at": "2026-05-01",
})

_INTERVIEW_MULTI_SLOT_RESPONSE = json.dumps({
    "kind": "interview_invite",
    "confidence": "high",
    "interview": {
        "round_type": "phone_screen",
        "scheduled_at": None,
        "scheduled_time": None,
        "interviewer_names": None,
        "location": None,
        "prep_notes": "Please select a 30-minute slot from the provided options",
        "links": ["https://calendly.com/recruiter/slots"],
    },
    "rejection": {
        "summary": None,
        "reasons": None,
        "links": [],
    },
    "received_at": "2026-05-02",
})

_REJECTION_RESPONSE = json.dumps({
    "kind": "rejection",
    "confidence": "high",
    "interview": {
        "round_type": None,
        "scheduled_at": None,
        "scheduled_time": None,
        "interviewer_names": None,
        "location": None,
        "prep_notes": None,
        "links": [],
    },
    "rejection": {
        "summary": "Application not progressed after review stage",
        "reasons": "High volume of applicants\nProfile did not match senior requirements",
        "links": [],
    },
    "received_at": "2026-05-03",
})

_UNKNOWN_RESPONSE = json.dumps({
    "kind": "unknown",
    "confidence": "high",
    "interview": {
        "round_type": None,
        "scheduled_at": None,
        "scheduled_time": None,
        "interviewer_names": None,
        "location": None,
        "prep_notes": None,
        "links": [],
    },
    "rejection": {
        "summary": None,
        "reasons": None,
        "links": [],
    },
    "received_at": None,
})


@pytest.mark.asyncio
async def test_extract_email_info_interview_confirmed():
    """Confirmed single-slot invite: kind, scheduled_at/time, and links are populated."""
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", llm_model="gpt-4o")

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = _make_openai_mock_client(_INTERVIEW_CONFIRMED_RESPONSE)
        result = await extract_email_info("You are invited for a technical interview...", settings)

    assert result["kind"] == "interview_invite"
    assert result["confidence"] == "high"
    assert result["interview"]["scheduled_at"] == "2026-05-10"
    assert result["interview"]["scheduled_time"] == "14:00"
    assert isinstance(result["interview"]["links"], list)
    assert len(result["interview"]["links"]) > 0
    assert result["rejection"]["summary"] is None
    assert result["rejection"]["links"] == []


@pytest.mark.asyncio
async def test_extract_email_info_interview_multi_slot():
    """Multiple candidate slots: scheduled_at and scheduled_time must be null."""
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", llm_model="gpt-4o")

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = _make_openai_mock_client(_INTERVIEW_MULTI_SLOT_RESPONSE)
        result = await extract_email_info(
            "Please pick one of the following slots: May 5 at 10:00, May 6 at 14:00...",
            settings,
        )

    assert result["kind"] == "interview_invite"
    assert result["interview"]["scheduled_at"] is None
    assert result["interview"]["scheduled_time"] is None


@pytest.mark.asyncio
async def test_extract_email_info_rejection():
    """Rejection email: kind and rejection.summary populated, interview fields null."""
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", llm_model="gpt-4o")

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = _make_openai_mock_client(_REJECTION_RESPONSE)
        result = await extract_email_info(
            "Unfortunately we will not be moving forward with your application...",
            settings,
        )

    assert result["kind"] == "rejection"
    assert result["rejection"]["summary"] is not None
    assert result["interview"]["scheduled_at"] is None
    assert result["interview"]["links"] == []


@pytest.mark.asyncio
async def test_extract_email_info_unknown():
    """Generic/unrelated email: kind=='unknown', both branches largely null."""
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", llm_model="gpt-4o")

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = _make_openai_mock_client(_UNKNOWN_RESPONSE)
        result = await extract_email_info("Thanks for signing up for our newsletter...", settings)

    assert result["kind"] == "unknown"
    assert result["interview"]["scheduled_at"] is None
    assert result["rejection"]["summary"] is None
    assert result["received_at"] is None


@pytest.mark.asyncio
async def test_extract_email_info_markdown_wrapped_json():
    """_parse_json strips markdown fences in the LLM response."""
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", llm_model="gpt-4o")
    wrapped = f"```json\n{_REJECTION_RESPONSE}\n```"

    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = _make_openai_mock_client(wrapped)
        result = await extract_email_info("Rejection notice", settings)

    assert result["kind"] == "rejection"
    assert result["rejection"]["summary"] is not None


# ── _web_search_tool ──────────────────────────────────────────────────────────

def test_web_search_tool_default():
    tool = _web_search_tool()
    assert tool == {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}


def test_web_search_tool_custom_max_uses():
    tool = _web_search_tool(max_uses=5)
    assert tool["max_uses"] == 5


# ── _call_anthropic payload & response parsing ────────────────────────────────

def _make_anthropic_mock_client(content_blocks: list) -> AsyncMock:
    """Return a patched AsyncClient that returns the given Anthropic content blocks."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"content": content_blocks}
    instance = AsyncMock()
    instance.post.return_value = mock_resp
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=False)
    return instance


@pytest.mark.asyncio
async def test_call_anthropic_payload_without_tools():
    """_call_anthropic omits 'tools' key and uses max_tokens 8192 when tools=None."""
    instance = _make_anthropic_mock_client([{"type": "text", "text": "result"}])
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await _call_anthropic(
            "https://api.anthropic.com/v1/messages", "key", "model", "sys", "usr"
        )
    payload = instance.post.call_args[1]["json"]
    assert "tools" not in payload
    assert payload["max_tokens"] == 8192
    assert result == "result"


@pytest.mark.asyncio
async def test_call_anthropic_payload_with_tools():
    """_call_anthropic includes 'tools' in payload and bumps max_tokens to 16384."""
    tools = [_web_search_tool()]
    # Simulate a tool-use response: tool blocks + text blocks
    content_blocks = [
        {"type": "server_tool_use", "id": "tu_01", "name": "web_search", "input": {"query": "ESA A2"}},
        {"type": "web_search_tool_result", "tool_use_id": "tu_01", "content": "..."},
        {"type": "text", "text": "Resolved: "},
        {"type": "text", "text": "€5,000/month"},
    ]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await _call_anthropic(
            "https://api.anthropic.com/v1/messages", "key", "model", "sys", "usr", tools=tools
        )
    payload = instance.post.call_args[1]["json"]
    assert payload["tools"] == tools
    assert payload["max_tokens"] == 16384
    # All text blocks concatenated in order
    assert result == "Resolved: €5,000/month"


@pytest.mark.asyncio
async def test_call_anthropic_concatenates_all_text_blocks():
    """Response with multiple text blocks → all text joined with no separator."""
    content_blocks = [
        {"type": "server_tool_use", "id": "x", "name": "web_search", "input": {}},
        {"type": "web_search_tool_result", "tool_use_id": "x", "content": "..."},
        {"type": "text", "text": "Hello "},
        {"type": "text", "text": "world"},
    ]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await _call_anthropic(
            "https://api.anthropic.com/v1/messages", "key", "model", "sys", "usr"
        )
    assert result == "Hello world"


@pytest.mark.asyncio
async def test_call_anthropic_raises_on_no_text_blocks():
    """Response with only tool blocks (no text) raises ValueError."""
    content_blocks = [
        {"type": "server_tool_use", "id": "x", "name": "web_search", "input": {}},
        {"type": "web_search_tool_result", "tool_use_id": "x", "content": "..."},
    ]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        with pytest.raises(ValueError, match="Claude returned no text content"):
            await _call_anthropic(
                "https://api.anthropic.com/v1/messages", "key", "model", "sys", "usr"
            )


# ── extract_job_info routing with search_enrichment_enabled ──────────────────

@pytest.mark.asyncio
async def test_extract_job_info_cliproxy_with_enrichment():
    """search_enrichment_enabled=True + cliproxy → _call_anthropic via /v1/messages with tools."""
    settings = Settings(
        llm_provider="cliproxy",
        cliproxy_base_url="http://localhost:8317",
        cliproxy_api_key="proxy-key",
        llm_model="claude-opus-4-6",
        search_enrichment_enabled=True,
    )
    content_blocks = [{"type": "text", "text": _SAMPLE_RESPONSE}]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await extract_job_info("Some JD with ESA A2 salary", settings)

    call_args = instance.post.call_args
    url = call_args[0][0]
    assert "localhost:8317" in url
    assert "/v1/messages" in url
    # tools were included in the payload
    payload = call_args[1]["json"]
    assert "tools" in payload
    assert any(t.get("type") == "web_search_20250305" for t in payload["tools"])
    # salary-grade instruction present in user turn
    user_content = payload["messages"][0]["content"]
    assert "web_search" in user_content
    assert result["company"] == "Acme Corp"


@pytest.mark.asyncio
async def test_extract_job_info_anthropic_with_enrichment():
    """search_enrichment_enabled=True + anthropic → _call_anthropic with public Anthropic URL."""
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-key",
        llm_model="claude-sonnet-4-6",
        search_enrichment_enabled=True,
    )
    content_blocks = [{"type": "text", "text": _SAMPLE_RESPONSE}]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await extract_job_info("Some JD with ESA A2 salary", settings)

    call_args = instance.post.call_args
    url = call_args[0][0]
    assert "api.anthropic.com" in url
    assert "/v1/messages" in url
    payload = call_args[1]["json"]
    assert "tools" in payload
    assert result["company"] == "Acme Corp"


@pytest.mark.asyncio
async def test_extract_job_info_enrichment_disabled_no_tools():
    """search_enrichment_enabled=False → no tools even for anthropic provider."""
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-key",
        llm_model="claude-sonnet-4-6",
        search_enrichment_enabled=False,
    )
    content_blocks = [{"type": "text", "text": _SAMPLE_RESPONSE}]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await extract_job_info("Some JD text", settings)

    payload = instance.post.call_args[1]["json"]
    assert "tools" not in payload
    # salary-grade instruction must NOT be in the user turn
    user_content = payload["messages"][0]["content"]
    assert "web_search" not in user_content
    assert result["company"] == "Acme Corp"


@pytest.mark.asyncio
async def test_extract_job_info_openai_ignores_enrichment_flag():
    """provider=openai → openai-compatible path even when enrichment flag is True."""
    settings = Settings(
        llm_provider="openai",
        openai_api_key="sk-test",
        llm_model="gpt-4o",
        search_enrichment_enabled=True,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {"choices": [{"message": {"content": _SAMPLE_RESPONSE}}]}
    instance = AsyncMock()
    instance.post.return_value = mock_resp
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=False)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await extract_job_info("Some JD text", settings)

    call_args = instance.post.call_args
    assert "api.openai.com" in call_args[0][0]
    assert "/v1/chat/completions" in call_args[0][0]
    # OpenAI-compatible path — no tools in payload
    payload = call_args[1]["json"]
    assert "tools" not in payload
    assert result["company"] == "Acme Corp"


# ── llm_call_with_trace ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_call_with_trace_rejects_non_anthropic():
    """ValueError is raised for providers other than anthropic / cliproxy."""
    for bad_provider in ("openai", "groq", "ollama"):
        settings = Settings(llm_provider=bad_provider)
        with pytest.raises(ValueError, match="requires anthropic or cliproxy provider"):
            await llm_call_with_trace("sys", "usr", settings, provider=bad_provider)


@pytest.mark.asyncio
async def test_llm_call_with_trace_basic_anthropic():
    """Text-only response: text populated, thinking empty, search_log empty."""
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        llm_model="claude-sonnet-4-6",
    )
    content_blocks = [{"type": "text", "text": "Hello from Claude"}]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await llm_call_with_trace("sys", "usr", settings)

    assert isinstance(result, LLMTraceResult)
    assert result.text == "Hello from Claude"
    assert result.thinking == ""
    assert result.search_log == []
    call_args = instance.post.call_args
    assert "api.anthropic.com" in call_args[0][0]


@pytest.mark.asyncio
async def test_llm_call_with_trace_extracts_thinking():
    """Thinking + text blocks: both captured correctly."""
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        llm_model="claude-sonnet-4-6",
    )
    content_blocks = [
        {"type": "thinking", "thinking": "Let me reason about this step by step."},
        {"type": "text", "text": "Final answer."},
    ]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await llm_call_with_trace("sys", "usr", settings, thinking_budget=10000)

    assert result.thinking == "Let me reason about this step by step."
    assert result.text == "Final answer."
    assert result.search_log == []


@pytest.mark.asyncio
async def test_llm_call_with_trace_extracts_search_log():
    """server_tool_use(web_search) + web_search_tool_result → search_log populated."""
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        llm_model="claude-sonnet-4-6",
    )
    content_blocks = [
        {
            "type": "server_tool_use",
            "id": "tu_01",
            "name": "web_search",
            "input": {"query": "interview preparation tips"},
        },
        {
            "type": "web_search_tool_result",
            "tool_use_id": "tu_01",
            "content": [
                {"type": "web_search_result", "url": "https://example.com/a", "title": "Article A"},
                {"type": "web_search_result", "url": "https://example.com/b", "title": "Article B"},
            ],
        },
        {"type": "text", "text": "Here is your prep guide."},
    ]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await llm_call_with_trace("sys", "usr", settings)

    assert result.text == "Here is your prep guide."
    assert len(result.search_log) == 2
    assert result.search_log[0] == {
        "query": "interview preparation tips",
        "url": "https://example.com/a",
        "title": "Article A",
    }
    assert result.search_log[1] == {
        "query": "interview preparation tips",
        "url": "https://example.com/b",
        "title": "Article B",
    }


@pytest.mark.asyncio
async def test_llm_call_with_trace_thinking_budget_sets_temperature_1():
    """With thinking_budget set: temperature==1, thinking param present, max_tokens >= budget+8192."""
    thinking_budget = 20000
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-ant-test",
        llm_model="claude-sonnet-4-6",
    )
    content_blocks = [
        {"type": "thinking", "thinking": "Deep thoughts."},
        {"type": "text", "text": "Answer."},
    ]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await llm_call_with_trace(
            "sys", "usr", settings, thinking_budget=thinking_budget
        )

    payload = instance.post.call_args[1]["json"]
    assert payload["temperature"] == 1
    assert payload["thinking"] == {"type": "enabled", "budget_tokens": thinking_budget}
    assert payload["max_tokens"] >= thinking_budget + 8192
    assert result.thinking == "Deep thoughts."
    assert result.text == "Answer."


@pytest.mark.asyncio
async def test_llm_call_with_trace_cliproxy():
    """cliproxy provider: request goes to cliproxy_base_url/v1/messages."""
    settings = Settings(
        llm_provider="cliproxy",
        cliproxy_base_url="http://localhost:8317",
        cliproxy_api_key="proxy-key",
        llm_model="claude-opus-4-6",
    )
    content_blocks = [{"type": "text", "text": "Cliproxy response"}]
    instance = _make_anthropic_mock_client(content_blocks)
    with patch("jam.llm.httpx.AsyncClient") as MockClient:
        MockClient.return_value = instance
        result = await llm_call_with_trace("sys", "usr", settings)

    assert isinstance(result, LLMTraceResult)
    assert result.text == "Cliproxy response"
    assert result.thinking == ""
    assert result.search_log == []
    call_args = instance.post.call_args
    assert "localhost:8317" in call_args[0][0]
    assert "/v1/messages" in call_args[0][0]
