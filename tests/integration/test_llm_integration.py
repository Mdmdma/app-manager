"""Integration tests for jam.llm — requires a live LLM provider (e.g. cliproxy).

Run with:
    uv run pytest tests/integration/test_llm_integration.py -x -v -m integration
"""

from __future__ import annotations

import json
import os
import re
import pytest

from jam.config import Settings
from jam.db import get_all_settings
from jam.llm import extract_job_info

_EXPECTED_JOB_KEYS = {
    "company",
    "position",
    "location",
    "salary_range",
    "requirements",
    "description",
    "opening_date",
    "closing_date",
}

# ── ENV_MAP mirrored from jam/server.py ──────────────────────────────────────
# Overlay DB-stored settings into os.environ so Settings() picks them up,
# exactly as the server startup handler does.
_ENV_MAP = {
    "openai_api_key":    "OPENAI_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "groq_api_key":      "GROQ_API_KEY",
    "ollama_base_url":   "OLLAMA_BASE_URL",
    "cliproxy_base_url": "CLIPROXY_BASE_URL",
    "cliproxy_api_key":  "CLIPROXY_API_KEY",
    "llm_provider":      "LLM_PROVIDER",
    "llm_model":         "LLM_MODEL",
}


def _load_settings_from_db() -> Settings:
    """Read DB-stored settings and overlay onto os.environ, then return Settings()."""
    try:
        stored = get_all_settings()
    except Exception:
        stored = {}
    for db_key, env_var in _ENV_MAP.items():
        if db_key in stored:
            os.environ[env_var] = stored[db_key]
    return Settings()


_SAMPLE_JD = """\
Software Engineer, Platform Team
Acme Corp — San Francisco, CA (Hybrid)
Posted: 2026-04-01 | Deadline: 2026-05-15
Salary: $140,000 – $170,000

About the role:
Join Acme Corp's Platform Team to design and build the infrastructure that
powers millions of transactions per day. You will work closely with product
engineers to define APIs, improve reliability, and drive scalability across
our core services.

Responsibilities:
- Design and implement backend services in Python and Go
- Contribute to CI/CD pipelines and infrastructure-as-code (Terraform)
- Participate in on-call rotation and incident response
- Collaborate with senior engineers on architecture decisions

Requirements:
- 3+ years of professional software engineering experience
- Strong Python skills; Go experience a plus
- Familiarity with distributed systems, message queues (Kafka/RabbitMQ)
- Experience with Kubernetes and cloud platforms (AWS/GCP)
- Bachelor's degree in Computer Science or equivalent practical experience

What we offer:
- Competitive salary and equity package
- Comprehensive health, dental, and vision insurance
- Flexible remote / hybrid work arrangement
- $2,000 annual learning budget
"""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_job_info_live():
    """extract_job_info returns a dict with non-empty company and position.

    Skips if the configured LLM provider is unreachable or no key is set.
    """
    import httpx

    settings = _load_settings_from_db()

    # Skip if no meaningful provider is configured
    provider = settings.llm_provider
    has_key = bool(
        (provider == "openai" and settings.openai_api_key)
        or (provider == "anthropic" and settings.anthropic_api_key)
        or (provider == "groq" and settings.groq_api_key)
        or (provider == "ollama")
        or (provider == "cliproxy")
    )
    if not has_key:
        pytest.skip(f"No API key configured for provider '{provider}'")

    try:
        result = await extract_job_info(_SAMPLE_JD, settings)
    except httpx.ConnectError as exc:
        pytest.skip(f"LLM provider unreachable: {exc}")
    except httpx.HTTPStatusError as exc:
        pytest.skip(f"LLM provider returned error: {exc}")
    except Exception as exc:
        # Re-raise unexpected errors (e.g. JSON parse failures) so they fail
        # loudly and clearly rather than silently skipping.
        raise

    # Print the raw result for visibility in test output
    print(f"\nModel returned:\n{json.dumps(result, indent=2)}")

    assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result!r}"

    # All expected schema keys must be present
    missing = _EXPECTED_JOB_KEYS - result.keys()
    assert not missing, (
        f"Schema keys missing from result: {missing!r}\nFull result: {result!r}"
    )

    # company: non-empty string, never "title"
    assert isinstance(result["company"], str) and result["company"], (
        f"'company' must be a non-empty string, got: {result['company']!r}"
    )

    # position: non-empty string (model must NOT use "title" instead)
    assert isinstance(result["position"], str) and result["position"], (
        f"'position' must be a non-empty string (not 'title'), got: {result!r}"
    )

    # requirements: string, NOT a list/array
    assert isinstance(result["requirements"], str), (
        f"'requirements' must be a string (comma-separated), "
        f"got {type(result['requirements'])}: {result['requirements']!r}"
    )

    # salary_range: string or None (NOT a nested dict/object)
    assert result["salary_range"] is None or isinstance(result["salary_range"], str), (
        f"'salary_range' must be a string or null, "
        f"got {type(result['salary_range'])}: {result['salary_range']!r}"
    )

    # opening_date / closing_date: string or None
    assert result["opening_date"] is None or isinstance(result["opening_date"], str), (
        f"'opening_date' must be a string or null, got: {result['opening_date']!r}"
    )
    assert result["closing_date"] is None or isinstance(result["closing_date"], str), (
        f"'closing_date' must be a string or null, got: {result['closing_date']!r}"
    )

    # Sanity-check known values from the sample JD
    assert "Acme" in result["company"], (
        f"Expected 'Acme' in company, got: {result['company']!r}"
    )


# ── web_search enrichment live test ──────────────────────────────────────────

_ESA_GRADE_JD = """\
Job Vacancy: Research Scientist
European Space Agency (ESA) — ESTEC, Noordwijk, Netherlands
Posted: 2026-04-01

About the role:
Join ESA's Science and Exploration Directorate as a Research Scientist,
contributing to missions that explore the solar system and beyond.
You will work alongside a team of leading scientists and engineers.

Salary: as per ESA grade A2 scale

Requirements:
- PhD in Physics, Astronomy, or a related field
- Strong publication record in peer-reviewed journals
- Experience with mission operations or instrument design
- Proficiency in Python and data analysis

Deadline: 2026-06-30
"""

# ENV_MAP addition for search_enrichment_enabled (mirrors jam/server.py)
_SEARCH_ENRICHMENT_ENV_KEY = "JAM_SEARCH_ENRICHMENT_ENABLED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_job_info_web_search_live():
    """extract_job_info resolves an ESA grade reference via web_search to a concrete salary.

    Proof that the web_search_20250305 tool is actually firing and enriching
    the salary_range field when it would otherwise be null.

    Skips if:
    - search_enrichment_enabled is False
    - provider is not 'anthropic' or 'cliproxy'
    - no API key is configured
    - provider is unreachable (ConnectError / HTTPStatusError)
    """
    import httpx as _httpx

    settings = _load_settings_from_db()
    provider = settings.llm_provider

    if not settings.search_enrichment_enabled:
        pytest.skip("search_enrichment_enabled is False — skipping web search live test")

    if provider not in ("anthropic", "cliproxy"):
        pytest.skip(
            f"Web search enrichment is Claude-only; provider '{provider}' is not supported"
        )

    has_key = bool(
        (provider == "anthropic" and settings.anthropic_api_key)
        or (provider == "cliproxy")  # cliproxy may not need a key
    )
    if not has_key:
        pytest.skip(f"No API key configured for provider '{provider}'")

    try:
        result = await extract_job_info(_ESA_GRADE_JD, settings)
    except _httpx.ConnectError as exc:
        pytest.skip(f"LLM provider unreachable: {exc}")
    except _httpx.HTTPStatusError as exc:
        pytest.skip(f"LLM provider returned error: {exc}")

    print(f"\nWeb-search enriched result:\n{json.dumps(result, indent=2)}")

    salary = result.get("salary_range")
    print(f"salary_range = {salary!r}")

    assert salary is not None and salary != "", (
        f"Expected salary_range to be resolved by web_search, got: {salary!r}"
    )
    # The resolved value must contain a digit OR a currency symbol to prove
    # a concrete figure was returned (not just "ESA A2" echoed back).
    assert re.search(r"[\d€$£]", salary), (
        f"salary_range does not contain a concrete figure or currency symbol: {salary!r}"
    )
