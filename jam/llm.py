"""LLM client for structured data extraction and document generation.

Supports OpenAI-compatible APIs (OpenAI, Groq, Ollama) and Anthropic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import httpx

from jam.config import Settings


@dataclass
class LLMTraceResult:
    """Result of an LLM call that captures text, thinking, and web-search trace.

    Attributes:
        text: Concatenation of all ``text`` content blocks in the response.
        thinking: Concatenation of all ``thinking`` content blocks (empty string
            when thinking was not enabled or the model produced no thinking).
        search_log: Flattened list of ``{query, url, title}`` dicts extracted from
            ``server_tool_use`` / ``web_search_tool_result`` block pairs in order
            of occurrence. Empty list when no web searches were performed.
    """

    text: str = ""
    thinking: str = ""
    search_log: list[dict] = field(default_factory=list)

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

_EMAIL_SYSTEM_PROMPT = """\
You are an email classifier that extracts structured information from job-application \
emails. Return ONLY a JSON object matching this exact schema — no markdown fences, no \
extra text:

{
  "kind": "interview_invite" | "rejection" | "unknown",
  "confidence": "high" | "medium" | "low",
  "interview": {
    "round_type": null | "phone_screen" | "technical" | "behavioral" | "hiring_manager" | "panel" | "other",
    "scheduled_at": null | "YYYY-MM-DD",
    "scheduled_time": null | "HH:MM",
    "interviewer_names": null | "Alice, Bob",
    "location": null | "address or primary meeting link",
    "prep_notes": null | "short summary of format/agenda",
    "links": []
  },
  "rejection": {
    "summary": null | "one-sentence outcome",
    "reasons": null | "reasons — one per line if multiple",
    "links": []
  },
  "received_at": null | "YYYY-MM-DD"
}

Rules:
- Return ONLY valid JSON — no markdown fences, no extra text.
- "kind" classifies the email. Use "unknown" if the email is neither an interview \
invitation nor a rejection/non-selection email.
- Only populate a field when the information is unambiguous and high-confidence. \
When in doubt, use null.
- If the email offers multiple candidate dates/times for the user to choose between, \
set "scheduled_at" and "scheduled_time" to null. Only populate them when a single \
date/time is confirmed.
- "links" must always be a JSON array (possibly empty). Deduplicate. Include all URLs \
found in the email (Zoom/Meet/Teams/calendar/doc links etc.).
- "round_type" must be one of the enumerated values or null.
- Dates are ISO (YYYY-MM-DD), times 24h (HH:MM).
- The object for the non-matching branch may contain all-null fields (e.g. when \
kind == "interview_invite", rejection.summary/reasons should be null and \
rejection.links an empty array)."""

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


def _web_search_tool(max_uses: int = 3) -> dict:
    """Return the Anthropic web_search_20250305 server-side tool spec."""
    return {"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}


async def _anthropic_request(
    url: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    *,
    tools: list | None = None,
    thinking_budget: int | None = None,
) -> list[dict]:
    """Low-level Anthropic Messages API call; returns raw ``content`` block list.

    When ``thinking_budget`` is set, extended thinking is enabled:
    - ``thinking`` param is added with ``budget_tokens=thinking_budget``
    - ``temperature`` is forced to 1 (Anthropic requirement)
    - ``max_tokens`` is set to ``max(16384, thinking_budget + 8192)``

    Without ``thinking_budget``:
    - ``temperature`` is 0.1
    - ``max_tokens`` is 8192, or 16384 when ``tools`` are provided
    """
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    if thinking_budget is not None and thinking_budget > 0:
        temperature = 1
        max_tokens = max(16384, thinking_budget + 8192)
    else:
        temperature = 0.1
        # Bump max_tokens when tools are in play to accommodate tool-use round trip.
        max_tokens = 16384 if tools else 8192

    payload: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "temperature": temperature,
    }
    if tools is not None:
        payload["tools"] = tools
    if thinking_budget is not None and thinking_budget > 0:
        payload["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["content"]


async def _call_anthropic(
    url: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    *,
    tools: list | None = None,
) -> str:
    content = await _anthropic_request(url, api_key, model, system, user, tools=tools)
    # Concatenate all text blocks in order; ignore tool-use/tool-result blocks.
    texts = [block["text"] for block in content if block.get("type") == "text"]
    if not texts:
        raise ValueError("Claude returned no text content")
    return "".join(texts)


def _parse_json(raw: str) -> dict:
    """Extract JSON from LLM response, tolerating markdown fences and prose preambles.

    Processing order:
    1. Strip whitespace; raise ValueError if empty.
    2. If a triple-backtick fence exists (with or without 'json' tag), use its contents.
    3. Otherwise, if content doesn't start with '{' or '[', locate the first '{' and
       matching last '}' (or '[' / ']') and take that substring.
    4. If no braces found at all, raise ValueError.
    5. Call json.loads — any JSONDecodeError propagates with its own message.
    """
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("LLM returned empty response")

    # Step 2: extract fenced block if present
    m = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(1).strip()
    else:
        # Step 3: locate the first JSON object or array; strip any leading/trailing
        # prose regardless of whether the content happens to start with '{' or '['.
        obj_start = cleaned.find("{")
        arr_start = cleaned.find("[")

        if obj_start == -1 and arr_start == -1:
            raise ValueError("LLM response contained no JSON object")

        if arr_start == -1 or (obj_start != -1 and obj_start < arr_start):
            # object wins
            end = cleaned.rfind("}")
            if end == -1:
                raise ValueError("LLM response contained no JSON object")
            cleaned = cleaned[obj_start : end + 1]
        else:
            # array wins
            end = cleaned.rfind("]")
            if end == -1:
                raise ValueError("LLM response contained no JSON object")
            cleaned = cleaned[arr_start : end + 1]

    return json.loads(cleaned)


async def llm_call(
    system: str,
    user: str,
    settings: Settings | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
    tools: list | None = None,
) -> str:
    """Generic LLM call dispatching to the configured provider.

    Used by generation nodes for document generation and analysis.

    The optional keyword-only ``provider`` and ``model`` arguments override the
    values from ``settings`` when provided (non-None).

    The optional keyword-only ``tools`` argument is forwarded to the Anthropic
    Messages API when the resolved provider is ``anthropic`` or ``cliproxy``.
    For other providers the argument is silently ignored (Claude-only feature).
    """
    settings = settings or Settings()
    provider = provider or settings.llm_provider
    model = model or settings.llm_model
    api_key = _api_key_for(settings, provider)

    if provider == "anthropic":
        anthropic_url = "https://api.anthropic.com/v1/messages"
        return await _call_anthropic(anthropic_url, api_key, model, system, user, tools=tools)
    elif provider == "cliproxy":
        cliproxy_messages_url = f"{settings.cliproxy_base_url.rstrip('/')}/v1/messages"
        return await _call_anthropic(cliproxy_messages_url, api_key, model, system, user, tools=tools)
    elif provider == "ollama":
        return await _call_openai_compatible(
            _get_ollama_url(settings), api_key, model, system, user
        )
    else:
        url = _OPENAI_COMPATIBLE_URLS.get(provider, _OPENAI_COMPATIBLE_URLS["openai"])
        return await _call_openai_compatible(url, api_key, model, system, user)


async def llm_call_with_trace(
    system: str,
    user: str,
    settings: Settings | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
    tools: list | None = None,
    thinking_budget: int | None = None,
) -> LLMTraceResult:
    """LLM call returning full trace: text, thinking blocks, and web-search log.

    Only supports ``anthropic`` and ``cliproxy`` providers (both use the
    Anthropic Messages API).  Raises ``ValueError`` for any other provider.

    When ``thinking_budget`` is set (and > 0), extended thinking is enabled:
    - ``thinking`` param is added to the request with the given budget
    - ``temperature`` is forced to 1 (Anthropic requirement)
    - ``max_tokens`` is set to ``max(16384, thinking_budget + 8192)``

    The returned :class:`LLMTraceResult` has:
    - ``text``: concatenation of all ``type=="text"`` content blocks
    - ``thinking``: concatenation of all ``type=="thinking"`` blocks' ``.thinking``
    - ``search_log``: flattened ``[{query, url, title}, ...]`` from paired
      ``server_tool_use(web_search)`` + ``web_search_tool_result`` blocks
    """
    settings = settings or Settings()
    provider = provider or settings.llm_provider
    model = model or settings.llm_model
    api_key = _api_key_for(settings, provider)

    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
    elif provider == "cliproxy":
        url = f"{settings.cliproxy_base_url.rstrip('/')}/v1/messages"
    else:
        raise ValueError("llm_call_with_trace requires anthropic or cliproxy provider")

    content = await _anthropic_request(
        url, api_key, model, system, user,
        tools=tools,
        thinking_budget=thinking_budget,
    )

    # Parse the response into the three result components.
    text_parts: list[str] = []
    thinking_parts: list[str] = []
    search_log: list[dict] = []

    # Build a lookup of server_tool_use id → query for pairing with results.
    pending_queries: dict[str, str] = {}

    for block in content:
        btype = block.get("type")

        if btype == "text":
            text_parts.append(block.get("text", ""))

        elif btype == "thinking":
            # Anthropic thinking blocks use the field name "thinking" (not "text").
            thinking_parts.append(block.get("thinking", ""))

        elif btype == "server_tool_use" and block.get("name") == "web_search":
            tool_id = block.get("id", "")
            query = (block.get("input") or {}).get("query", "")
            pending_queries[tool_id] = query

        elif btype == "web_search_tool_result":
            tool_use_id = block.get("tool_use_id", "")
            query = pending_queries.get(tool_use_id, "")
            result_entries = block.get("content") or []
            if isinstance(result_entries, list):
                for entry in result_entries:
                    if not isinstance(entry, dict):
                        continue
                    url_val = entry.get("url", "")
                    title_val = entry.get("title", "")
                    if url_val or title_val:
                        search_log.append(
                            {"query": query, "url": url_val, "title": title_val}
                        )

    return LLMTraceResult(
        text="".join(text_parts),
        thinking="".join(thinking_parts),
        search_log=search_log,
    )


async def extract_job_info(text: str, settings: Settings | None = None) -> dict:
    """Send webpage text to the configured LLM and return parsed job info.

    Returns a dict with keys: company, position, location, salary_range,
    requirements, description, opening_date, closing_date.
    Raises on LLM or parse errors.

    The user turn repeats the exact field names and types so that models which
    ignore the system prompt (e.g. via a proxy) still receive the full schema
    in the turn they do attend to.

    When ``settings.search_enrichment_enabled`` is True and the provider is
    ``anthropic`` or ``cliproxy``, the ``web_search_20250305`` tool is passed
    so the model can resolve salary grades / public-sector pay scales to
    concrete figures.
    """
    settings = settings or Settings()

    # Decide whether to include the web-search tool for this call.
    use_tools = (
        settings.search_enrichment_enabled
        and settings.llm_provider in ("anthropic", "cliproxy")
    )
    active_tools: list | None = [_web_search_tool()] if use_tools else None

    # Build the salary-grade search instruction (only when tools are active).
    salary_search_line = (
        "If the posting references a salary grade, pay scale, or public-sector"
        " band (e.g. \"ESA A2\", \"EU AD7\", \"GS-13\", \"TVöD E14\") without"
        " a concrete figure, use the web_search tool to resolve it to a"
        " concrete \u20ac / $ / \u00a3 amount or range before returning JSON."
        " Include the resolved amount in the salary_range field.\n"
    ) if use_tools else ""

    user = (
        "Extract the job posting details as a single JSON object with EXACTLY"
        " these fields and no others:\n\n"
        "{\n"
        '  "company": string,\n'
        '  "position": string,\n'
        '  "location": string or null,\n'
        '  "salary_range": string or null,\n'
        '  "requirements": string (brief comma-separated list, NOT an array),\n'
        '  "description": string (2-3 sentence summary),\n'
        '  "opening_date": string "YYYY-MM-DD" or null,\n'
        '  "closing_date": string "YYYY-MM-DD" or null\n'
        "}\n\n"
        "Do NOT use different field names (e.g. \"title\" instead of \"position\","
        " or \"salary\" as a nested object)."
        " Do NOT add extra fields."
        " Return ONLY the JSON object, no prose, no markdown fences.\n\n"
        "Job posting text:\n"
        f"{text}\n\n"
        f"{salary_search_line}"
        "Return ONLY the JSON object matching the schema above."
    )
    raw = await llm_call(_SYSTEM_PROMPT, user, settings, tools=active_tools)
    return _parse_json(raw)


async def extract_email_info(text: str, settings: Settings | None = None) -> dict:
    """Send email text to the configured LLM and return structured classification.

    Returns a dict with keys: kind, confidence, interview, rejection, received_at.
    - kind: "interview_invite" | "rejection" | "unknown"
    - confidence: "high" | "medium" | "low"
    - interview: dict with round_type, scheduled_at, scheduled_time,
      interviewer_names, location, prep_notes, links
    - rejection: dict with summary, reasons, links
    - received_at: ISO date string or null

    Raises on LLM or parse errors.

    The user turn repeats the exact field names and types so that models which
    ignore the system prompt (e.g. via a proxy) still receive the full schema
    in the turn they do attend to.
    """
    settings = settings or Settings()
    user = (
        "Classify this email as a single JSON object with EXACTLY this schema"
        " and no other fields:\n\n"
        "{\n"
        '  "kind": "interview_invite" | "rejection" | "unknown",\n'
        '  "confidence": "high" | "medium" | "low",\n'
        '  "interview": {\n'
        '    "round_type": null | "phone_screen" | "technical" | "behavioral"'
        ' | "hiring_manager" | "panel" | "other",\n'
        '    "scheduled_at": null | "YYYY-MM-DD",\n'
        '    "scheduled_time": null | "HH:MM",\n'
        '    "interviewer_names": null | "Alice, Bob",\n'
        '    "location": null | "address or primary meeting link",\n'
        '    "prep_notes": null | "short summary of format/agenda",\n'
        '    "links": []\n'
        "  },\n"
        '  "rejection": {\n'
        '    "summary": null | "one-sentence outcome",\n'
        '    "reasons": null | "reasons — one per line if multiple",\n'
        '    "links": []\n'
        "  },\n"
        '  "received_at": null | "YYYY-MM-DD"\n'
        "}\n\n"
        "Do NOT use different field names or add extra fields."
        " Return ONLY the JSON object, no prose, no markdown fences.\n\n"
        "Email text:\n"
        f"{text}\n\n"
        "Return ONLY the JSON object matching the schema above."
    )
    raw = await llm_call(_EMAIL_SYSTEM_PROMPT, user, settings)
    return _parse_json(raw)
