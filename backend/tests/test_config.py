from __future__ import annotations

import importlib
from typing import List


ENV_KEYS: List[str] = [
    "FOKS_ENV",
    "LMSTUDIO_BASE_URL",
    "LMSTUDIO_MODEL",
    "LMSTUDIO_API_KEY",
    "FOKS_MODEL_DIRECTORIES",
    "FBP_BACKEND_BASE_URL",
    "FOKS_DEFAULT_TIMEOUT_SECONDS",
    "FOKS_STREAM_TIMEOUT_SECONDS",
    "FOKS_DEFAULT_RETRY_ATTEMPTS",
    "FOKS_RETRY_BACKOFF_SECONDS",
    "FOKS_LOG_FILE",
    "FOKS_LOG_LEVEL",
    "FOKS_LOG_JSON",
    "FOKS_LOG_MAX_BYTES",
    "FOKS_LOG_BACKUP_COUNT",
    "FOKS_ENABLE_MONITORING",
    "FOKS_ENABLE_RATE_LIMIT",
    "FOKS_ENABLE_M3_MIDDLEWARE",
    "FOKS_REQUIRE_AUTH",
    "FOKS_ALLOWED_ORIGINS",
]


def _reload_config():
    import app.config as app_config

    return importlib.reload(app_config)


def test_settings_defaults(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    app_config = _reload_config()
    settings = app_config.get_settings()

    assert settings.environment == "development"
    assert settings.lmstudio_base_url == "http://localhost:1234/v1"
    assert settings.model_directories == ["/Volumes/MICRO/LM_STUDIO_MODELS"]
    assert settings.fbp_backend_base_url == "http://localhost:8000"
    assert settings.fbp_socket_path == "/tmp/fbp.sock"
    assert settings.fbp_transport == "socket"
    assert settings.fbp_port == 8000
    assert settings.fbp_base_url.startswith("http+unix://")
    assert settings.default_timeout_seconds == 30
    assert settings.default_retry_attempts == 3
    assert settings.retry_backoff_seconds == 2.0
    assert settings.log_level == "INFO"
    assert settings.log_format_json is True
    assert settings.enable_monitoring_middleware is True
    assert settings.enable_rate_limit_middleware is True
    assert settings.enable_m3_middleware is True
    assert settings.require_auth_middleware is False
    assert "http://localhost" in settings.allowed_origins


def test_settings_env_overrides(monkeypatch):
    monkeypatch.setenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:9999/v1")
    monkeypatch.setenv("FOKS_MODEL_DIRECTORIES", "/tmp/models-a,/tmp/models-b")
    monkeypatch.setenv("FBP_BACKEND_BASE_URL", "http://fbp.local/api")
    monkeypatch.setenv("FBP_SOCKET_PATH", "/tmp/custom.sock")
    monkeypatch.setenv("FBP_TRANSPORT", "port")
    monkeypatch.setenv("FBP_PORT", "9000")
    monkeypatch.setenv("FOKS_DEFAULT_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("FOKS_DEFAULT_RETRY_ATTEMPTS", "5")
    monkeypatch.setenv("FOKS_RETRY_BACKOFF_SECONDS", "1.5")
    monkeypatch.setenv("FOKS_LOG_LEVEL", "debug")
    monkeypatch.setenv("FOKS_LOG_JSON", "false")
    monkeypatch.setenv("FOKS_ENABLE_MONITORING", "false")
    monkeypatch.setenv("FOKS_ALLOWED_ORIGINS", "https://foo,https://bar")

    app_config = _reload_config()
    settings = app_config.get_settings()

    assert settings.lmstudio_base_url == "http://127.0.0.1:9999/v1"
    assert settings.model_directories == ["/tmp/models-a", "/tmp/models-b"]
    assert settings.fbp_backend_base_url == "http://fbp.local/api"
    assert settings.fbp_socket_path == "/tmp/custom.sock"
    assert settings.fbp_transport == "port"
    assert settings.fbp_port == 9000
    assert settings.fbp_base_url == "http://localhost:9000"
    assert settings.default_timeout_seconds == 45
    assert settings.default_retry_attempts == 5
    assert settings.retry_backoff_seconds == 1.5
    assert settings.log_level == "DEBUG"
    assert settings.log_format_json is False
    assert settings.enable_monitoring_middleware is False
    assert settings.allowed_origins == ["https://foo", "https://bar"]

