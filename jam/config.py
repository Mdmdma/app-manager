from dataclasses import dataclass, field
import os


@dataclass
class Settings:
    kb_api_url: str = field(
        default_factory=lambda: os.getenv("JAM_KB_API_URL", "http://localhost:8000/api/v1")
    )
    port: int = field(
        default_factory=lambda: int(os.getenv("JAM_PORT", "8001"))
    )
    # LLM provider settings
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    cliproxy_base_url: str = field(default_factory=lambda: os.getenv("CLIPROXY_BASE_URL", "http://localhost:8317"))
    cliproxy_api_key: str = field(default_factory=lambda: os.getenv("CLIPROXY_API_KEY", ""))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    # LaTeX template defaults
    cv_latex_template: str = field(default_factory=lambda: os.getenv("JAM_CV_LATEX_TEMPLATE", ""))
    cover_letter_latex_template: str = field(default_factory=lambda: os.getenv("JAM_COVER_LETTER_LATEX_TEMPLATE", ""))
    # Gmail OAuth settings
    gmail_client_id: str = field(default_factory=lambda: os.getenv("GMAIL_CLIENT_ID", ""))
    gmail_client_secret: str = field(default_factory=lambda: os.getenv("GMAIL_CLIENT_SECRET", ""))
    gmail_refresh_token: str = field(default_factory=lambda: os.getenv("GMAIL_REFRESH_TOKEN", ""))
    gmail_user_email: str = field(default_factory=lambda: os.getenv("GMAIL_USER_EMAIL", ""))
    # Microsoft Graph (Outlook Calendar) OAuth settings
    ms_graph_client_id: str = field(default_factory=lambda: os.getenv("MS_GRAPH_CLIENT_ID", ""))
    ms_graph_client_secret: str = field(default_factory=lambda: os.getenv("MS_GRAPH_CLIENT_SECRET", ""))
    ms_graph_tenant: str = field(default_factory=lambda: os.getenv("MS_GRAPH_TENANT", "common"))
    ms_graph_redirect_uri: str = field(default_factory=lambda: os.getenv("MS_GRAPH_REDIRECT_URI", "http://localhost:8001/ms_graph/callback"))
    ms_graph_refresh_token: str = field(default_factory=lambda: os.getenv("MS_GRAPH_REFRESH_TOKEN", ""))
    ms_graph_access_token: str = field(default_factory=lambda: os.getenv("MS_GRAPH_ACCESS_TOKEN", ""))
    ms_graph_token_expires_at: str = field(default_factory=lambda: os.getenv("MS_GRAPH_TOKEN_EXPIRES_AT", ""))
    ms_graph_user_email: str = field(default_factory=lambda: os.getenv("MS_GRAPH_USER_EMAIL", ""))
    ms_graph_calendar_id: str = field(default_factory=lambda: os.getenv("MS_GRAPH_CALENDAR_ID", ""))
    # Calendar settings
    calendar_timezone: str = field(default_factory=lambda: os.getenv("JAM_CALENDAR_TIMEZONE", "UTC"))
    calendar_default_duration_minutes: int = field(
        default_factory=lambda: int(os.getenv("JAM_CALENDAR_DEFAULT_DURATION_MINUTES", "60"))
    )
    # KB retrieval settings
    kb_retrieval_namespaces: str = field(default_factory=lambda: os.getenv("JAM_KB_RETRIEVAL_NAMESPACES", ""))
    kb_retrieval_n_results: int = field(default_factory=lambda: int(os.getenv("JAM_KB_RETRIEVAL_N_RESULTS", "5")))
    kb_retrieval_padding: int = field(default_factory=lambda: int(os.getenv("JAM_KB_RETRIEVAL_PADDING", "0")))
    kb_include_namespaces: str = field(default_factory=lambda: os.getenv("JAM_KB_INCLUDE_NAMESPACES", ""))
    # Search enrichment
    search_enrichment_enabled: bool = field(
        default_factory=lambda: os.getenv("JAM_SEARCH_ENRICHMENT_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
    )
    # Personal info (PDF metadata)
    personal_full_name: str = field(default_factory=lambda: os.getenv("JAM_PERSONAL_FULL_NAME", ""))
    personal_email: str = field(default_factory=lambda: os.getenv("JAM_PERSONAL_EMAIL", ""))
    personal_phone: str = field(default_factory=lambda: os.getenv("JAM_PERSONAL_PHONE", ""))
    personal_website: str = field(default_factory=lambda: os.getenv("JAM_PERSONAL_WEBSITE", ""))
    personal_address: str = field(default_factory=lambda: os.getenv("JAM_PERSONAL_ADDRESS", ""))
    personal_photo: str = field(default_factory=lambda: os.getenv("JAM_PERSONAL_PHOTO", ""))
    personal_signature: str = field(default_factory=lambda: os.getenv("JAM_PERSONAL_SIGNATURE", ""))
    # Interview prep guide generation settings
    prompt_generate_prep_guide: str = field(
        default_factory=lambda: os.getenv("JAM_PROMPT_GENERATE_PREP_GUIDE", "")
    )
    prep_guide_max_web_searches: int = field(
        default_factory=lambda: int(os.getenv("JAM_PREP_GUIDE_MAX_WEB_SEARCHES", "100"))
    )
    prep_guide_thinking_budget: int = field(
        default_factory=lambda: int(os.getenv("JAM_PREP_GUIDE_THINKING_BUDGET", "16000"))
    )
    step_model_generate_prep_guide: str = field(
        default_factory=lambda: os.getenv("JAM_STEP_MODEL_GENERATE_PREP_GUIDE", "")
    )
