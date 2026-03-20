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
