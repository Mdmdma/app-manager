import os

from jam.config import Settings


def test_defaults(monkeypatch):
    """Settings should have sensible defaults without any env vars."""
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY",
                "OLLAMA_BASE_URL", "CLIPROXY_BASE_URL", "CLIPROXY_API_KEY", "LLM_PROVIDER", "LLM_MODEL",
                "JAM_KB_API_URL", "JAM_PORT",
                "JAM_CV_LATEX_TEMPLATE", "JAM_COVER_LETTER_LATEX_TEMPLATE",
                "GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET",
                "GMAIL_REFRESH_TOKEN", "GMAIL_USER_EMAIL",
                "JAM_KB_RETRIEVAL_NAMESPACES", "JAM_KB_RETRIEVAL_N_RESULTS",
                "JAM_KB_RETRIEVAL_PADDING", "JAM_KB_INCLUDE_NAMESPACES",
                "JAM_PERSONAL_FULL_NAME", "JAM_PERSONAL_EMAIL",
                "JAM_PERSONAL_PHONE", "JAM_PERSONAL_WEBSITE",
                "JAM_PERSONAL_ADDRESS",
                "JAM_PERSONAL_PHOTO", "JAM_PERSONAL_SIGNATURE"):
        monkeypatch.delenv(var, raising=False)
    s = Settings()
    assert s.kb_api_url == "http://localhost:8000/api/v1"
    assert s.port == 8001
    assert s.openai_api_key == ""
    assert s.anthropic_api_key == ""
    assert s.groq_api_key == ""
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.cliproxy_base_url == "http://localhost:8317"
    assert s.cliproxy_api_key == ""
    assert s.llm_provider == "openai"
    assert s.llm_model == "gpt-4o"
    assert s.cv_latex_template == ""
    assert s.cover_letter_latex_template == ""
    assert s.gmail_client_id == ""
    assert s.gmail_client_secret == ""
    assert s.gmail_refresh_token == ""
    assert s.gmail_user_email == ""
    assert s.kb_retrieval_namespaces == ""
    assert s.kb_retrieval_n_results == 5
    assert s.kb_retrieval_padding == 0
    assert s.kb_include_namespaces == ""
    assert s.personal_full_name == ""
    assert s.personal_email == ""
    assert s.personal_phone == ""
    assert s.personal_website == ""
    assert s.personal_address == ""
    assert s.personal_photo == ""
    assert s.personal_signature == ""


def test_env_overrides(monkeypatch):
    """Settings should read from JAM_* environment variables."""
    monkeypatch.setenv("JAM_KB_API_URL", "http://kb:9000/api/v1")
    monkeypatch.setenv("JAM_PORT", "9999")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-anthropic")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-groq")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("CLIPROXY_BASE_URL", "http://proxy:9999")
    monkeypatch.setenv("CLIPROXY_API_KEY", "sk-cliproxy-test")
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
    assert s.cliproxy_base_url == "http://proxy:9999"
    assert s.cliproxy_api_key == "sk-cliproxy-test"
    assert s.llm_provider == "anthropic"
    assert s.llm_model == "claude-3-5-sonnet-20241022"
    assert s.cv_latex_template == "\\documentclass{article}"
    assert s.cover_letter_latex_template == "\\documentclass{letter}"
    monkeypatch.setenv("GMAIL_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "test-refresh-token")
    monkeypatch.setenv("GMAIL_USER_EMAIL", "user@example.com")
    s2 = Settings()
    assert s2.gmail_client_id == "test-client-id"
    assert s2.gmail_client_secret == "test-client-secret"
    assert s2.gmail_refresh_token == "test-refresh-token"
    assert s2.gmail_user_email == "user@example.com"
    monkeypatch.setenv("JAM_KB_RETRIEVAL_NAMESPACES", '["ns-1","ns-2"]')
    monkeypatch.setenv("JAM_KB_RETRIEVAL_N_RESULTS", "10")
    monkeypatch.setenv("JAM_KB_RETRIEVAL_PADDING", "2")
    monkeypatch.setenv("JAM_KB_INCLUDE_NAMESPACES", '["ns-3"]')
    s3 = Settings()
    assert s3.kb_retrieval_namespaces == '["ns-1","ns-2"]'
    assert s3.kb_retrieval_n_results == 10
    assert s3.kb_retrieval_padding == 2
    assert s3.kb_include_namespaces == '["ns-3"]'
    monkeypatch.setenv("JAM_PERSONAL_FULL_NAME", "Jane Doe")
    monkeypatch.setenv("JAM_PERSONAL_EMAIL", "jane@example.com")
    monkeypatch.setenv("JAM_PERSONAL_PHONE", "+1-555-0100")
    monkeypatch.setenv("JAM_PERSONAL_WEBSITE", "https://janedoe.dev")
    monkeypatch.setenv("JAM_PERSONAL_ADDRESS", "123 Main St, Springfield")
    s4 = Settings()
    assert s4.personal_full_name == "Jane Doe"
    assert s4.personal_email == "jane@example.com"
    assert s4.personal_phone == "+1-555-0100"
    assert s4.personal_website == "https://janedoe.dev"
    assert s4.personal_address == "123 Main St, Springfield"
    monkeypatch.setenv("JAM_PERSONAL_PHOTO", "data:image/png;base64,abc123")
    monkeypatch.setenv("JAM_PERSONAL_SIGNATURE", "data:image/png;base64,abc123")
    s5 = Settings()
    assert s5.personal_photo == "data:image/png;base64,abc123"
    assert s5.personal_signature == "data:image/png;base64,abc123"
