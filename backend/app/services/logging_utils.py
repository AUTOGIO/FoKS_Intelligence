from __future__ import annotations

import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

from app.config import settings

_LOGGER_CACHE: Dict[str, logging.Logger] = {}

SENSITIVE_PATTERNS = [
    (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\s]+)', 'api_key="***"'),
    (r'password["\']?\s*[:=]\s*["\']?([^"\'\s]+)', 'password="***"'),
    (r'token["\']?\s*[:=]\s*["\']?([^"\'\s]+)', 'token="***"'),
    (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s]+)', 'secret="***"'),
    (
        r'authorization["\']?\s*[:=]\s*["\']?bearer\s+([^"\'\s]+)',
        'authorization="Bearer ***"',
        re.IGNORECASE,
    ),
    (r'x-api-key["\']?\s*[:=]\s*["\']?([^"\'\s]+)', 'x-api-key="***"', re.IGNORECASE),
]
SENSITIVE_KEYS = {"api_key", "token", "password", "secret", "authorization", "x-api-key"}


def sanitize_text(text: str) -> str:
    """Mask sensitive tokens before persisting logs."""
    if not text:
        return text
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        if len(pattern) == 3:
            regex, replacement, flags = pattern
            sanitized = re.sub(regex, replacement, sanitized, flags=flags)
        else:
            regex, replacement = pattern
            sanitized = re.sub(regex, replacement, sanitized)
    return sanitized


def sanitize_payload(payload: Any) -> Any:
    """Recursively sanitize payload structures."""
    if payload is None:
        return None
    if isinstance(payload, dict):
        sanitized: Dict[str, Any] = {}
        for key, value in payload.items():
            normalized_key = key.lower().replace("-", "_") if isinstance(key, str) else key
            if isinstance(normalized_key, str) and normalized_key in SENSITIVE_KEYS:
                if normalized_key == "authorization" and isinstance(value, str):
                    sanitized[key] = "Bearer ***"
                else:
                    sanitized[key] = "***"
                continue
            sanitized[key] = sanitize_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    if isinstance(payload, str):
        return sanitize_text(payload)
    return payload


class JSONFormatter(logging.Formatter):
    """Formatter that emits structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        event_name = getattr(record, "event", record.getMessage())
        payload = sanitize_payload(getattr(record, "payload", record.__dict__.get("payload")))

        log_data = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "event": sanitize_text(str(event_name)),
            "payload": payload,
        }

        if record.exc_info:
            log_data["exception"] = sanitize_text(self.formatException(record.exc_info))

        return json.dumps(log_data, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Human readable formatter that still sanitizes sensitive data."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return sanitize_text(original)


def _get_log_level() -> int:
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(settings.log_level, logging.INFO)


def _build_formatter() -> logging.Formatter:
    if settings.log_format_json:
        return JSONFormatter()
    return TextFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def _build_file_handler(formatter: logging.Formatter) -> RotatingFileHandler:
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler


def get_logger(name: str) -> logging.Logger:
    """Return a shared structured logger with file + console handlers."""
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    formatter = _build_formatter()

    logger = logging.getLogger(name)
    logger.setLevel(_get_log_level())
    logger.propagate = False

    if not logger.handlers:
        file_handler = _build_file_handler(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(_get_log_level())
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    _LOGGER_CACHE[name] = logger
    return logger

