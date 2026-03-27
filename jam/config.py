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
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    # LaTeX template defaults
    cv_latex_template: str = field(default_factory=lambda: os.getenv("JAM_CV_LATEX_TEMPLATE", ""))
    cover_letter_latex_template: str = field(default_factory=lambda: os.getenv("JAM_COVER_LETTER_LATEX_TEMPLATE", ""))
