from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict

from app.config import settings

_LOGGER_CACHE: Dict[str, logging.Logger] = {}


def _build_handler() -> RotatingFileHandler:
    """Create a rotating file handler pointing to the configured log file."""
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
    )
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    return handler


def get_logger(name: str) -> logging.Logger:
    """Return a shared logger configured for both console and file output."""
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = _build_handler()
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Avoid duplicating handlers if this is called repeatedly.
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    _LOGGER_CACHE[name] = logger
    return logger
from __future__ import annotations

import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings


def sanitize_secrets(text: str) -> str:
    """
    Sanitize secrets from log messages.

    Args:
        text: Text that may contain secrets

    Returns:
        Text with secrets masked
    """
    if not text:
        return text

    # List of patterns to mask (API keys, passwords, tokens, etc.)
    patterns = [
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'api_key="***"'),
        (r'password["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'password="***"'),
        (r'token["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'token="***"'),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'secret="***"'),
        (r'authorization["\']?\s*[:=]\s*["\']?bearer\s+([^"\'\s]+)', r'authorization="Bearer ***"', re.IGNORECASE),
        (r'x-api-key["\']?\s*[:=]\s*["\']?([^"\'\s]+)', r'x-api-key="***"', re.IGNORECASE),
    ]

    sanitized = text
    for pattern_info in patterns:
        if len(pattern_info) == 3:
            pattern, replacement, flags = pattern_info
            sanitized = re.sub(pattern, replacement, sanitized, flags=flags)
        else:
            pattern, replacement = pattern_info
            sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        # Sanitize secrets from log message
        message = sanitize_secrets(message)

        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            log_data["exception"] = sanitize_secrets(exc_text)

        # Add extra fields if present
        if hasattr(record, "extra"):
            extra = record.extra.copy()
            # Sanitize extra fields
            for key, value in extra.items():
                if isinstance(value, str):
                    extra[key] = sanitize_secrets(value)
            log_data.update(extra)

        return json.dumps(log_data, ensure_ascii=False)


class SecureFormatter(logging.Formatter):
    """Secure formatter that sanitizes secrets from log messages."""

    def format(self, record: logging.LogRecord) -> str:
        # Get original formatted message
        original = super().format(record)
        # Sanitize secrets
        return sanitize_secrets(original)


def get_log_level() -> int:
    """Get log level from settings."""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(settings.log_level, logging.INFO)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(get_log_level())

    if not logger.handlers:
        log_path = Path(settings.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = RotatingFileHandler(
            log_path,
            maxBytes=10_000_000,  # 10MB
            backupCount=10,  # Keep 10 backup files
            encoding="utf-8",
        )

        if settings.log_format_json:
            formatter = JSONFormatter()
        else:
            # Use secure formatter to sanitize secrets even in text format
            formatter = SecureFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        handler.setFormatter(formatter)

        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(get_log_level())

        logger.addHandler(handler)
        logger.addHandler(console)

    return logger

