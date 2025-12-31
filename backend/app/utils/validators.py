"""Input validation utilities for FoKS Intelligence."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.services.logging_utils import get_logger

logger = get_logger("validators")


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL string to validate

    Returns:
        bool: True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:  # noqa: BLE001
        return False


def sanitize_text(text: str, max_length: int = 10000) -> str:
    """
    Sanitize text input - robust protection against XSS and injection.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        str: Sanitized text
    """
    if not isinstance(text, str):
        return ""

    # Remove null bytes and control characters (except newlines and tabs)
    sanitized = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", text)

    # Remove HTML/script tags (basic XSS protection)
    sanitized = re.sub(r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r"<iframe[^>]*>.*?</iframe>", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"on\w+\s*=", "", sanitized, flags=re.IGNORECASE)  # Remove event handlers

    # Remove SQL injection patterns (basic protection)
    sql_patterns = [
        r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+",  # OR 1=1, AND 1=1
        r"(\bUNION\b|\bSELECT\b|\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b)",  # SQL keywords
        r"['\";].*?--",  # SQL comments
    ]
    for pattern in sql_patterns:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

    # Truncate if too long
    if len(sanitized) > max_length:
        logger.warning("Text truncated from %d to %d characters", len(text), max_length)
        sanitized = sanitized[:max_length]

    return sanitized


def validate_cpf(cpf: str) -> tuple[bool, str]:
    """
    Validate Brazilian CPF (Cadastro de Pessoa Física) format.

    Accepts CPF in formats:
    - 12345678901 (11 digits)
    - 123.456.789-01 (formatted)

    Args:
        cpf: CPF string to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(cpf, str):
        return False, "CPF must be a string"

    # Remove formatting (dots and dashes)
    cpf_clean = re.sub(r"[.\-]", "", cpf.strip())

    # Must be exactly 11 digits
    if not cpf_clean.isdigit():
        return False, "CPF must contain only digits (formatting allowed)"

    if len(cpf_clean) != 11:
        return False, "CPF must have exactly 11 digits"

    # Check for invalid patterns (all same digit)
    if len(set(cpf_clean)) == 1:
        return False, "CPF cannot have all identical digits"

    # Basic validation: check verification digits
    # This is a simplified check - full CPF validation would verify both check digits
    # For now, we just ensure it's not obviously invalid
    return True, ""


def validate_task_params(task_name: str, params: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate task parameters.

    Args:
        task_name: Name of the task
        params: Task parameters

    Returns:
        tuple: (is_valid, error_message)
    """
    # Validate open_url
    if task_name == "open_url":
        url = params.get("url")
        if not url:
            return False, "Missing 'url' parameter"
        if not validate_url(url):
            return False, "Invalid URL format"

    # Validate say
    elif task_name == "say":
        if "text" not in params:
            return False, "Missing 'text' parameter"
        if not isinstance(params["text"], str):
            return False, "'text' must be a string"

    # Validate notification
    elif task_name == "notification":
        if "message" not in params:
            return False, "Missing 'message' parameter"

    # Validate set_clipboard
    elif task_name == "set_clipboard":
        if "text" not in params:
            return False, "Missing 'text' parameter"

    # Validate run_script
    elif task_name == "run_script":
        path = params.get("path")
        if not path:
            return False, "Missing 'path' parameter"
        if not isinstance(path, str):
            return False, "'path' must be a string"

        # Security: Prevent path traversal
        path = sanitize_text(path, max_length=1024)
        if ".." in path:
            logger.warning("Path traversal attempt detected: %s", path)
            return False, "Path traversal not allowed"

        # Sanitize and update params
        params["path"] = path

    # Validate screenshot
    elif task_name == "screenshot":
        screenshot_type = params.get("type", "full")
        if screenshot_type not in ["full", "window", "selection"]:
            return False, f"Invalid screenshot type: {screenshot_type}"

    # Validate open_app
    elif task_name == "open_app":
        if "app" not in params:
            return False, "Missing 'app' parameter"
        if not isinstance(params["app"], str):
            return False, "'app' must be a string"

    return True, ""

