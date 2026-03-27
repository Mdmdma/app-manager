import os

from jam.config import Settings


def test_defaults(monkeypatch):
    """Settings should have sensible defaults without any env vars."""
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY",
                "OLLAMA_BASE_URL", "LLM_PROVIDER", "LLM_MODEL",
                "JAM_KB_API_URL", "JAM_PORT",
                "JAM_CV_LATEX_TEMPLATE", "JAM_COVER_LETTER_LATEX_TEMPLATE"):
        monkeypatch.delenv(var, raising=False)
    s = Settings()
    assert s.kb_api_url == "http://localhost:8000/api/v1"
    assert s.port == 8001
    assert s.openai_api_key == ""
    assert s.anthropic_api_key == ""
    assert s.groq_api_key == ""
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.llm_provider == "openai"
    assert s.llm_model == "gpt-4o"
    assert s.cv_latex_template == ""
    assert s.cover_letter_latex_template == ""


def test_env_overrides(monkeypatch):
    """Settings should read from JAM_* environment variables."""
    monkeypatch.setenv("JAM_KB_API_URL", "http://kb:9000/api/v1")
    monkeypatch.setenv("JAM_PORT", "9999")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-groq")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
    monkeypatch.setenv("JAM_CV_LATEX_TEMPLATE", "\\documentclass{article}")
    monkeypatch.setenv("JAM_COVER_LETTER_LATEX_TEMPLATE", "\\documentclass{letter}")
    s = Settings()
    assert s.kb_api_url == "http://kb:9000/api/v1"
    assert s.port == 9999
    assert s.openai_api_key == "sk-test-openai"
    assert s.anthropic_api_key == "sk-test-anthropic"
    assert s.groq_api_key == "gsk-test-groq"
    assert s.ollama_base_url == "http://ollama:11434"
    assert s.llm_provider == "anthropic"
    assert s.llm_model == "claude-3-5-sonnet-20241022"
    assert s.cv_latex_template == "\\documentclass{article}"
    assert s.cover_letter_latex_template == "\\documentclass{letter}"
