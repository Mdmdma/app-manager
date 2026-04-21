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
                "JAM_PERSONAL_PHOTO", "JAM_PERSONAL_SIGNATURE",
                "JAM_SEARCH_ENRICHMENT_ENABLED",
                "JAM_PROMPT_GENERATE_PREP_GUIDE",
                "JAM_PREP_GUIDE_MAX_WEB_SEARCHES",
                "JAM_PREP_GUIDE_THINKING_BUDGET",
                "JAM_STEP_MODEL_GENERATE_PREP_GUIDE",
                "MS_GRAPH_CLIENT_ID", "MS_GRAPH_CLIENT_SECRET",
                "MS_GRAPH_TENANT", "MS_GRAPH_REDIRECT_URI",
                "MS_GRAPH_REFRESH_TOKEN", "MS_GRAPH_ACCESS_TOKEN",
                "MS_GRAPH_TOKEN_EXPIRES_AT", "MS_GRAPH_USER_EMAIL",
                "MS_GRAPH_CALENDAR_ID",
                "JAM_CALENDAR_TIMEZONE",
                "JAM_CALENDAR_DEFAULT_DURATION_MINUTES"):
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
    assert s.search_enrichment_enabled is True
    assert s.prompt_generate_prep_guide == ""
    assert s.prep_guide_max_web_searches == 100
    assert s.prep_guide_thinking_budget == 16000
    assert s.step_model_generate_prep_guide == ""
    assert s.ms_graph_client_id == ""
    assert s.ms_graph_client_secret == ""
    assert s.ms_graph_tenant == "common"
    assert s.ms_graph_redirect_uri == "http://localhost:8001/ms_graph/callback"
    assert s.ms_graph_refresh_token == ""
    assert s.ms_graph_access_token == ""
    assert s.ms_graph_token_expires_at == ""
    assert s.ms_graph_user_email == ""
    assert s.ms_graph_calendar_id == ""
    assert s.calendar_timezone == "UTC"
    assert s.calendar_default_duration_minutes == 60


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
    monkeypatch.setenv("JAM_SEARCH_ENRICHMENT_ENABLED", "0")
    s6 = Settings()
    assert s6.search_enrichment_enabled is False
    monkeypatch.setenv("JAM_PROMPT_GENERATE_PREP_GUIDE", "You are an interview coach.")
    monkeypatch.setenv("JAM_PREP_GUIDE_MAX_WEB_SEARCHES", "50")
    monkeypatch.setenv("JAM_PREP_GUIDE_THINKING_BUDGET", "8000")
    monkeypatch.setenv("JAM_STEP_MODEL_GENERATE_PREP_GUIDE", "anthropic:claude-opus-4-5")
    s7 = Settings()
    assert s7.prompt_generate_prep_guide == "You are an interview coach."
    assert s7.prep_guide_max_web_searches == 50
    assert s7.prep_guide_thinking_budget == 8000
    assert s7.step_model_generate_prep_guide == "anthropic:claude-opus-4-5"
    monkeypatch.setenv("MS_GRAPH_CLIENT_ID", "ms-client-id")
    monkeypatch.setenv("MS_GRAPH_CLIENT_SECRET", "ms-client-secret")
    monkeypatch.setenv("MS_GRAPH_TENANT", "mytenant.onmicrosoft.com")
    monkeypatch.setenv("MS_GRAPH_REDIRECT_URI", "http://localhost:9000/ms_graph/callback")
    monkeypatch.setenv("MS_GRAPH_REFRESH_TOKEN", "ms-refresh-token")
    monkeypatch.setenv("MS_GRAPH_ACCESS_TOKEN", "ms-access-token")
    monkeypatch.setenv("MS_GRAPH_TOKEN_EXPIRES_AT", "2026-12-31T23:59:59Z")
    monkeypatch.setenv("MS_GRAPH_USER_EMAIL", "user@outlook.com")
    monkeypatch.setenv("MS_GRAPH_CALENDAR_ID", "AAMkAGI=")
    monkeypatch.setenv("JAM_CALENDAR_TIMEZONE", "Europe/Berlin")
    monkeypatch.setenv("JAM_CALENDAR_DEFAULT_DURATION_MINUTES", "30")
    s8 = Settings()
    assert s8.ms_graph_client_id == "ms-client-id"
    assert s8.ms_graph_client_secret == "ms-client-secret"
    assert s8.ms_graph_tenant == "mytenant.onmicrosoft.com"
    assert s8.ms_graph_redirect_uri == "http://localhost:9000/ms_graph/callback"
    assert s8.ms_graph_refresh_token == "ms-refresh-token"
    assert s8.ms_graph_access_token == "ms-access-token"
    assert s8.ms_graph_token_expires_at == "2026-12-31T23:59:59Z"
    assert s8.ms_graph_user_email == "user@outlook.com"
    assert s8.ms_graph_calendar_id == "AAMkAGI="
    assert s8.calendar_timezone == "Europe/Berlin"
    assert s8.calendar_default_duration_minutes == 30


def test_search_enrichment_enabled_parsing(monkeypatch):
    """search_enrichment_enabled parses truthy/falsy strings correctly."""
    for truthy in ("1", "true", "True", "TRUE", "yes", "YES", "on", "ON"):
        monkeypatch.setenv("JAM_SEARCH_ENRICHMENT_ENABLED", truthy)
        assert Settings().search_enrichment_enabled is True, f"expected True for {truthy!r}"

    for falsy in ("0", "false", "False", "FALSE", "no", "NO", "off", "OFF", ""):
        monkeypatch.setenv("JAM_SEARCH_ENRICHMENT_ENABLED", falsy)
        assert Settings().search_enrichment_enabled is False, f"expected False for {falsy!r}"
