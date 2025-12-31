"""Helper utilities for FoKS Intelligence."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime
from typing import Any


def generate_request_id() -> str:
    """
    Generate a unique request ID.

    Returns:
        str: Unique request ID based on timestamp and random hash
    """
    timestamp = datetime.now().isoformat()
    hash_obj = hashlib.md5(timestamp.encode())
    return hash_obj.hexdigest()[:12]


def encode_base64_image(image_path: str) -> str:
    """
    Encode image file to base64.

    Args:
        image_path: Path to image file

    Returns:
        str: Base64 encoded image string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def format_response_time(seconds: float) -> str:
    """
    Format response time in human-readable format.

    Args:
        seconds: Time in seconds

    Returns:
        str: Formatted time string
    """
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    else:
        return f"{seconds:.2f}s"


def safe_get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary value.

    Args:
        data: Dictionary to search
        keys: Keys to traverse
        default: Default value if key not found

    Returns:
        Value at nested key or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix

