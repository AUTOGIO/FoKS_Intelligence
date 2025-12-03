from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Centralized configuration for the FoKS Intelligence backend."""

    app_name: str = "FoKS Intelligence Global Interface"
    environment: str = Field(default_factory=lambda: os.getenv("FOKS_ENV", "development"))
    lmstudio_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "LMSTUDIO_BASE_URL",
            "http://localhost:1234/v1/chat/completions",
        )
    )
    lmstudio_model: str = Field(default_factory=lambda: os.getenv("LMSTUDIO_MODEL", "qwen2.5-14b"))
    lmstudio_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("LMSTUDIO_API_KEY"))
    log_file_path: str = Field(
        default_factory=lambda: os.getenv(
            "FOKS_LOG_FILE",
            "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/logs/app.log",
        )
    )
    allowed_origins: List[str] = [
        "http://localhost",
        "http://127.0.0.1",
        "x-shortcuts://callback",
    ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
