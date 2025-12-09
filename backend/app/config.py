from __future__ import annotations

import os
from functools import lru_cache
import multiprocessing
from pathlib import Path
import platform
from typing import List, Optional

from pydantic import BaseModel, Field, validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


def _bool_env(key: str, default: bool) -> bool:
    """Return boolean environment variable with safe fallback."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _list_env(key: str, default: List[str]) -> List[str]:
    """Return list from env var separated by commas."""
    value = os.getenv(key)
    if value is None:
        return default
    # Filter empty chunks to avoid accidental blanks.
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_apple_silicon() -> bool:
    machine = platform.machine().lower()
    processor = platform.processor().lower()
    return "arm" in machine or "apple" in processor


class Settings(BaseModel):
    """Centralized configuration for the FoKS Intelligence backend."""

    app_name: str = "FoKS Intelligence Global Interface"
    environment: str = Field(default_factory=lambda: os.getenv("FOKS_ENV", "development"))

    # LM Studio & model registry
    lmstudio_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "LMSTUDIO_BASE_URL",
            "http://localhost:1234/v1",
        )
    )
    lmstudio_model: str = Field(default_factory=lambda: os.getenv("LMSTUDIO_MODEL", "qwen2.5-14b"))
    lmstudio_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("LMSTUDIO_API_KEY"))
    model_directories: List[str] = Field(
        default_factory=lambda: _list_env(
            "FOKS_MODEL_DIRECTORIES",
            ["/Volumes/MICRO/LM_STUDIO_MODELS"],
        )
    )

    # External backends
    fbp_backend_base_url: str = Field(
        default_factory=lambda: os.getenv("FBP_BACKEND_BASE_URL", "http://localhost:8000")
    )

    # Networking defaults
    default_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_DEFAULT_TIMEOUT_SECONDS", "30"))
    )
    stream_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_STREAM_TIMEOUT_SECONDS", "60"))
    )
    default_retry_attempts: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_DEFAULT_RETRY_ATTEMPTS", "3"))
    )
    retry_backoff_seconds: float = Field(
        default_factory=lambda: float(os.getenv("FOKS_RETRY_BACKOFF_SECONDS", "2.0"))
    )

    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("FOKS_API_KEY"))
    database_url: Optional[str] = Field(default_factory=lambda: os.getenv("DATABASE_URL"))
    use_postgresql: bool = Field(default_factory=lambda: _bool_env("FOKS_USE_POSTGRESQL", False))
    database_path: str = Field(
        default_factory=lambda: os.getenv(
            "FOKS_DATABASE_PATH",
            "/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/data/foks_conversations.db",
        )
    )

    # Logging configuration
    log_file_path: str = Field(
        default_factory=lambda: os.getenv(
            "FOKS_LOG_FILE",
            str(LOGS_DIR / "app.log"),
        )
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("FOKS_LOG_LEVEL", "INFO").upper()
    )
    log_format_json: bool = Field(default_factory=lambda: _bool_env("FOKS_LOG_JSON", True))
    log_max_bytes: int = Field(default_factory=lambda: int(os.getenv("FOKS_LOG_MAX_BYTES", "10485760")))
    log_backup_count: int = Field(default_factory=lambda: int(os.getenv("FOKS_LOG_BACKUP_COUNT", "10")))

    # Middleware flags
    enable_monitoring_middleware: bool = Field(
        default_factory=lambda: _bool_env("FOKS_ENABLE_MONITORING", True)
    )
    enable_rate_limit_middleware: bool = Field(
        default_factory=lambda: _bool_env("FOKS_ENABLE_RATE_LIMIT", True)
    )
    enable_m3_middleware: bool = Field(
        default_factory=lambda: _bool_env("FOKS_ENABLE_M3_MIDDLEWARE", True)
    )
    require_auth_middleware: bool = Field(
        default_factory=lambda: _bool_env("FOKS_REQUIRE_AUTH", False)
    )
    rate_limit_requests_per_minute: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_RATE_LIMIT_RPM", "60"))
    )
    rate_limit_use_token_bucket: bool = Field(
        default_factory=lambda: _bool_env("FOKS_RATE_LIMIT_USE_TOKEN_BUCKET", False)
    )
    rate_limit_burst_capacity: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_RATE_LIMIT_BURST", "30"))
    )

    # Webhooks
    webhook_enabled: bool = Field(
        default_factory=lambda: _bool_env("FOKS_WEBHOOK_ENABLED", False)
    )
    webhook_urls: List[str] = Field(
        default_factory=lambda: _list_env("FOKS_WEBHOOK_URLS", [])
    )

    # Caching
    cache_enabled: bool = Field(
        default_factory=lambda: _bool_env("FOKS_CACHE_ENABLED", False)
    )

    # Security / CORS
    allowed_origins: List[str] = Field(
        default_factory=lambda: _list_env(
            "FOKS_ALLOWED_ORIGINS",
            [
                "http://localhost",
                "http://127.0.0.1",
                "x-shortcuts://callback",
            ],
        )
    )
    # Hardware / optimization settings
    hardware_model: str = Field(default_factory=lambda: platform.machine())
    cpu_cores: int = Field(default_factory=lambda: multiprocessing.cpu_count())
    memory_gb: int = Field(default_factory=lambda: int(os.getenv("FOKS_MEMORY_GB", "16")))
    max_request_size_mb: int = Field(default_factory=lambda: int(os.getenv("FOKS_MAX_REQUEST_MB", "10")))
    optimal_workers: int = Field(default_factory=lambda: int(os.getenv("FOKS_OPTIMAL_WORKERS", "4")))
    max_concurrent_tasks: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_MAX_CONCURRENT_TASKS", "32"))
    )
    enable_neural_engine: bool = Field(
        default_factory=lambda: _bool_env("FOKS_ENABLE_NEURAL_ENGINE", True)
    )
    is_apple_silicon: bool = Field(default_factory=_is_apple_silicon)
    is_m3: bool = Field(default_factory=lambda: _bool_env("FOKS_IS_M3", False))

    class Config:
        validate_assignment = True

    @validator("log_level", pre=True)
    def normalize_log_level(cls, value):
        if not value:
            return "INFO"
        return str(value).upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


def reload_settings() -> Settings:
    """Clear cache and reload settings (useful for tests)."""
    global settings  # type: ignore[global-variable-not-assigned]
    get_settings.cache_clear()
    settings = get_settings()
    return settings


settings = get_settings()
