"""Tests for helper utilities."""

from __future__ import annotations

import base64
import tempfile
import os

import pytest

from app.utils.helpers import (
    encode_base64_image,
    format_response_time,
    generate_request_id,
    safe_get_nested,
    truncate_text,
)


class TestHelpers:
    """Test suite for helper utilities."""

    def test_generate_request_id(self) -> None:
        """Test request ID generation."""
        req_id = generate_request_id()
        assert isinstance(req_id, str)
        assert len(req_id) == 12

    def test_format_response_time(self) -> None:
        """Test response time formatting."""
        assert "μs" in format_response_time(0.0001)
        assert "ms" in format_response_time(0.1)
        assert "s" in format_response_time(1.5)

    def test_safe_get_nested(self) -> None:
        """Test safe nested dictionary access."""
        data = {"a": {"b": {"c": "value"}}}
        assert safe_get_nested(data, "a", "b", "c") == "value"
        assert safe_get_nested(data, "a", "b", "d") is None
        assert safe_get_nested(data, "a", "b", "d", default="default") == "default"

    def test_truncate_text(self) -> None:
        """Test text truncation."""
        long_text = "a" * 150
        truncated = truncate_text(long_text, max_length=100)
        assert len(truncated) == 100
        assert truncated.endswith("...")

        short_text = "short"
        assert truncate_text(short_text, max_length=100) == short_text

    def test_encode_base64_image(self) -> None:
        """Test base64 image encoding."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            encoded = encode_base64_image(temp_path)
            assert isinstance(encoded, str)
            # Verify it's valid base64
            decoded = base64.b64decode(encoded)
            assert decoded == b"fake image data"
        finally:
            os.unlink(temp_path)

