from __future__ import annotations

import multiprocessing
import os
import platform
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


def _bool_env(key: str, default: bool) -> bool:
    """Return boolean environment variable with safe fallback."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _list_env(key: str, default: list[str]) -> list[str]:
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
    lmstudio_api_key: str | None = Field(default_factory=lambda: os.getenv("LMSTUDIO_API_KEY"))
    model_directories: list[str] = Field(
        default_factory=lambda: _list_env(
            "FOKS_MODEL_DIRECTORIES",
            ["/Volumes/MICRO/LM_STUDIO_MODELS"],
        )
    )

    # Local Identity Guard & Model Locking
    local_identity_guard: bool = Field(
        default_factory=lambda: _bool_env("FOKS_LOCAL_IDENTITY_GUARD", True)
    )
    local_system_prompt: str = Field(
        default_factory=lambda: os.getenv(
            "FOKS_LOCAL_SYSTEM_PROMPT",
            "You are a helpful AI assistant running locally on the user's machine via LM Studio. "
            "You do not have any cloud connection, external servers, or corporate affiliation. "
            "Never reference OpenAI, Anthropic, Google, Meta, Microsoft, or any external AI provider. "
            "You are a local, private, and independent assistant.\n\n"
            "You have access to real-time system metrics provided in the [REAL-TIME SYSTEM CONTEXT] block. "
            "Use this data to answer user queries about server status, system resources, active workflows, "
            "and running tasks accurately. The context block includes CPU usage, memory usage, system uptime, "
            "active automations, and server status information.",
        )
    )
    cloud_leakage_patterns: list[str] = Field(
        default_factory=lambda: _list_env(
            "FOKS_CLOUD_LEAKAGE_PATTERNS",
            [
                r"\bOpenAI\b",
                r"\bChatGPT\b",
                r"\bGPT-[34]\b",
                r"\bAnthropic\b",
                r"\bClaude\b",
                r"\bGoogle\s+AI\b",
                r"\bGemini\b",
                r"\bBard\b",
                r"\bMicrosoft\b",
                r"\bAzure\s+AI\b",
                r"\bCopilot\b",
                r"\bAmazon\s+Bedrock\b",
                r"\bAWS\s+AI\b",
                r"\b(developed|created|made|trained)\s+by\s+(OpenAI|Anthropic|Google|Meta|Microsoft)\b",
            ],
        )
    )
    local_fallback_response: str = Field(
        default_factory=lambda: os.getenv(
            "FOKS_LOCAL_FALLBACK_RESPONSE",
            "I am a local AI assistant running on your machine. How can I help you today?",
        )
    )
    locked_chat_model: str = Field(
        default_factory=lambda: os.getenv("FOKS_LOCKED_CHAT_MODEL", "qwen3-14b-mlx")
    )
    locked_reasoning_model: str = Field(
        default_factory=lambda: os.getenv("FOKS_LOCKED_REASONING_MODEL", "deepseek-r1-qwen3-8b-mlx")
    )
    locked_embedding_model: str = Field(
        default_factory=lambda: os.getenv("FOKS_LOCKED_EMBEDDING_MODEL", "qwen3-embedding-4b-mlx")
    )
    locked_vision_model: str = Field(
        default_factory=lambda: os.getenv("FOKS_LOCKED_VISION_MODEL", "qwen3-vision-mlx")
    )
    locked_scientific_model: str = Field(
        default_factory=lambda: os.getenv("FOKS_LOCKED_SCIENTIFIC_MODEL", "granite-3.1-8b-mlx")
    )
    lmstudio_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_LMSTUDIO_TIMEOUT_SECONDS", "120"))
    )

    # External URLs (for Cloudflare Zero Trust tunnel access)
    foks_external_url: str = Field(
        default_factory=lambda: os.getenv("FOKS_EXTERNAL_URL", "https://foks.giovannini.us")
    )
    fbp_external_url: str = Field(
        default_factory=lambda: os.getenv("FBP_EXTERNAL_URL", "https://fbp.giovannini.us")
    )
    # Cloudflare Zero Trust headers (for access control validation)
    cloudflare_access_header: str = Field(
        default_factory=lambda: os.getenv("CF_ACCESS_HEADER", "Cf-Access-Jwt-Assertion")
    )
    cloudflare_client_id_header: str = Field(
        default_factory=lambda: os.getenv("CF_CLIENT_ID_HEADER", "Cf-Access-Client-Id")
    )

    # External backends
    fbp_backend_base_url: str = Field(
        default_factory=lambda: os.getenv("FBP_BACKEND_BASE_URL", "http://localhost:8000")
    )
    fbp_socket_path: str = Field(
        default_factory=lambda: os.getenv("FBP_SOCKET_PATH", "/tmp/fbp.sock")
    )
    fbp_transport: str = Field(default_factory=lambda: os.getenv("FBP_TRANSPORT", "socket"))
    fbp_port: int = Field(default_factory=lambda: int(os.getenv("FBP_PORT", "8000")))
    oase_base_url: str = Field(
        default_factory=lambda: os.getenv("OASE_BASE_URL", "http://localhost:8000")
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

    api_key: str | None = Field(default_factory=lambda: os.getenv("FOKS_API_KEY"))
    database_url: str | None = Field(default_factory=lambda: os.getenv("DATABASE_URL"))
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
    log_level: str = Field(default_factory=lambda: os.getenv("FOKS_LOG_LEVEL", "INFO").upper())
    log_format_json: bool = Field(default_factory=lambda: _bool_env("FOKS_LOG_JSON", True))
    log_max_bytes: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_LOG_MAX_BYTES", "10485760"))
    )
    log_backup_count: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_LOG_BACKUP_COUNT", "10"))
    )

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
    webhook_enabled: bool = Field(default_factory=lambda: _bool_env("FOKS_WEBHOOK_ENABLED", False))
    webhook_urls: list[str] = Field(default_factory=lambda: _list_env("FOKS_WEBHOOK_URLS", []))

    # Caching
    cache_enabled: bool = Field(default_factory=lambda: _bool_env("FOKS_CACHE_ENABLED", False))

    # Security / CORS
    # Includes Cloudflare Zero Trust tunnel domains
    allowed_origins: list[str] = Field(
        default_factory=lambda: _list_env(
            "FOKS_ALLOWED_ORIGINS",
            [
                "http://localhost",
                "http://127.0.0.1",
                "https://localhost",
                "https://127.0.0.1",
                "x-shortcuts://callback",
                # Cloudflare Zero Trust tunnel domains
                "https://foks.giovannini.us",
                "https://fbp.giovannini.us",
                "https://giovannini.us",
                # Allow all subdomains of giovannini.us (for flexibility)
                "https://*.giovannini.us",
            ],
        )
    )
    # Hardware / optimization settings
    hardware_model: str = Field(default_factory=lambda: platform.machine())
    cpu_cores: int = Field(default_factory=lambda: multiprocessing.cpu_count())
    memory_gb: int = Field(default_factory=lambda: int(os.getenv("FOKS_MEMORY_GB", "16")))
    max_request_size_mb: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_MAX_REQUEST_MB", "10"))
    )
    optimal_workers: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_OPTIMAL_WORKERS", "4"))
    )
    max_concurrent_tasks: int = Field(
        default_factory=lambda: int(os.getenv("FOKS_MAX_CONCURRENT_TASKS", "32"))
    )
    enable_neural_engine: bool = Field(
        default_factory=lambda: _bool_env("FOKS_ENABLE_NEURAL_ENGINE", True)
    )
    is_apple_silicon: bool = Field(default_factory=_is_apple_silicon)
    is_m3: bool = Field(default_factory=lambda: _bool_env("FOKS_IS_M3", False))

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str | None) -> str:
        if not value:
            return "INFO"
        return str(value).upper()

    @property
    def fbp_base_url(self) -> str:
        """
        Return FBP base URL based on transport preference.

        Note: When using socket transport, returns regular HTTP URL.
        The UDS transport is configured separately in FBPClient.
        """
        if self.fbp_transport.lower() == "socket":
            # For UDS transport, use regular HTTP URL
            # The socket path is handled by httpx.AsyncHTTPTransport(uds=...)
            return "http://localhost"
        if self.fbp_backend_base_url:
            return self.fbp_backend_base_url.rstrip("/")
        return f"http://localhost:{self.fbp_port}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


def reload_settings() -> Settings:
    """Clear cache and reload settings (useful for tests)."""
    global settings
    get_settings.cache_clear()
    settings = get_settings()
    return settings


settings = get_settings()
