"""LLM client for structured data extraction and document generation.

Supports OpenAI-compatible APIs (OpenAI, Groq, Ollama) and Anthropic.
"""

from __future__ import annotations

import json
import re

import httpx

from jam.config import Settings

_SYSTEM_PROMPT = """\
You are a job posting parser. Extract structured information from the provided \
job posting text. Return ONLY a JSON object with these fields:

{
  "company": "Company name",
  "position": "Job title / position name",
  "location": "Location (city, state/country) or 'Remote' or 'Hybrid'",
  "salary_range": "Salary range if mentioned, else null",
  "requirements": "Key requirements as a brief comma-separated list",
  "description": "2-3 sentence summary of the role",
  "opening_date": "Date the position was posted/opened (ISO format YYYY-MM-DD), else null",
  "closing_date": "Application deadline / closing date (ISO format YYYY-MM-DD), else null"
}

Rules:
- Return ONLY valid JSON, no markdown fences, no extra text.
- If a field cannot be determined from the text, use null.
- Dates must be in ISO format (YYYY-MM-DD) when found.
- company and position must never be null — infer from context if needed."""

_OPENAI_COMPATIBLE_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
}


def _get_ollama_url(settings: Settings) -> str:
    base = settings.ollama_base_url.rstrip("/")
    return f"{base}/v1/chat/completions"


def _get_cliproxy_url(settings: Settings) -> str:
    base = settings.cliproxy_base_url.rstrip("/")
    return f"{base}/v1/chat/completions"


def _api_key_for(settings: Settings, provider: str | None = None) -> str:
    p = provider or settings.llm_provider
    keys = {
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
        "groq": settings.groq_api_key,
        "ollama": "ollama",
        "cliproxy": settings.cliproxy_api_key,
    }
    return keys.get(p, "")


async def _call_openai_compatible(
    url: str, api_key: str, model: str, system: str, user: str
) -> str:
    headers = {"Content-Type": "application/json"}
    if api_key and api_key != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"]


async def _call_anthropic(api_key: str, model: str, system: str, user: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 8192,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["content"][0]["text"]


def _parse_json(raw: str) -> dict:
    """Extract JSON from LLM response, tolerating markdown fences."""
    cleaned = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(1).strip()
    return json.loads(cleaned)


async def llm_call(
    system: str,
    user: str,
    settings: Settings | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """Generic LLM call dispatching to the configured provider.

    Used by generation nodes for document generation and analysis.

    The optional keyword-only ``provider`` and ``model`` arguments override the
    values from ``settings`` when provided (non-None).
    """
    settings = settings or Settings()
    provider = provider or settings.llm_provider
    model = model or settings.llm_model
    api_key = _api_key_for(settings, provider)

    if provider == "anthropic":
        return await _call_anthropic(api_key, model, system, user)
    elif provider == "ollama":
        return await _call_openai_compatible(
            _get_ollama_url(settings), api_key, model, system, user
        )
    elif provider == "cliproxy":
        return await _call_openai_compatible(
            _get_cliproxy_url(settings), api_key, model, system, user
        )
    else:
        url = _OPENAI_COMPATIBLE_URLS.get(provider, _OPENAI_COMPATIBLE_URLS["openai"])
        return await _call_openai_compatible(url, api_key, model, system, user)


async def extract_job_info(text: str, settings: Settings | None = None) -> dict:
    """Send webpage text to the configured LLM and return parsed job info.

    Returns a dict with keys: company, position, location, salary_range,
    requirements, description.  Raises on LLM or parse errors.
    """
    settings = settings or Settings()
    raw = await llm_call(_SYSTEM_PROMPT, text, settings)
    return _parse_json(raw)
