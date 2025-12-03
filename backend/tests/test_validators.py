"""Tests for validators module."""

from __future__ import annotations

import pytest

from app.utils.validators import sanitize_text, validate_task_params, validate_url


class TestValidateURL:
    """Tests for validate_url function."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert validate_url("http://example.com") is True

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert validate_url("https://example.com/path") is True

    def test_valid_url_with_port(self):
        """Test valid URL with port."""
        assert validate_url("http://localhost:8000") is True

    def test_invalid_url_no_scheme(self):
        """Test invalid URL without scheme."""
        assert validate_url("example.com") is False

    def test_invalid_url_no_netloc(self):
        """Test invalid URL without netloc."""
        assert validate_url("http://") is False

    def test_invalid_url_empty_string(self):
        """Test invalid empty URL."""
        assert validate_url("") is False

    def test_invalid_url_malformed(self):
        """Test invalid malformed URL."""
        assert validate_url("not a url") is False


class TestSanitizeText:
    """Tests for sanitize_text function."""

    def test_sanitize_normal_text(self):
        """Test sanitizing normal text."""
        text = "Hello, World!"
        assert sanitize_text(text) == "Hello, World!"

    def test_sanitize_text_with_newlines(self):
        """Test sanitizing text with newlines."""
        text = "Line 1\nLine 2\nLine 3"
        assert sanitize_text(text) == "Line 1\nLine 2\nLine 3"

    def test_sanitize_text_with_tabs(self):
        """Test sanitizing text with tabs."""
        text = "Column1\tColumn2\tColumn3"
        assert sanitize_text(text) == "Column1\tColumn2\tColumn3"

    def test_sanitize_text_removes_null_bytes(self):
        """Test sanitizing removes null bytes."""
        text = "Hello\x00World"
        assert sanitize_text(text) == "HelloWorld"

    def test_sanitize_text_removes_control_chars(self):
        """Test sanitizing removes control characters."""
        text = "Hello\x01\x02\x03World"
        assert sanitize_text(text) == "HelloWorld"

    def test_sanitize_text_truncates_long_text(self):
        """Test sanitizing truncates text that exceeds max_length."""
        text = "a" * 20000
        result = sanitize_text(text, max_length=100)
        assert len(result) == 100
        assert result == "a" * 100

    def test_sanitize_text_non_string_input(self):
        """Test sanitizing non-string input returns empty string."""
        assert sanitize_text(123) == ""
        assert sanitize_text(None) == ""
        assert sanitize_text([]) == ""


class TestValidateTaskParams:
    """Tests for validate_task_params function."""

    def test_validate_open_url_valid(self):
        """Test validating open_url task with valid URL."""
        is_valid, error = validate_task_params("open_url", {"url": "http://example.com"})
        assert is_valid is True
        assert error == ""

    def test_validate_open_url_missing_url(self):
        """Test validating open_url task without URL."""
        is_valid, error = validate_task_params("open_url", {})
        assert is_valid is False
        assert "Missing 'url' parameter" in error

    def test_validate_open_url_invalid_url(self):
        """Test validating open_url task with invalid URL."""
        is_valid, error = validate_task_params("open_url", {"url": "not-a-url"})
        assert is_valid is False
        assert "Invalid URL format" in error

    def test_validate_say_valid(self):
        """Test validating say task with valid text."""
        is_valid, error = validate_task_params("say", {"text": "Hello"})
        assert is_valid is True
        assert error == ""

    def test_validate_say_missing_text(self):
        """Test validating say task without text."""
        is_valid, error = validate_task_params("say", {})
        assert is_valid is False
        assert "Missing 'text' parameter" in error

    def test_validate_say_non_string_text(self):
        """Test validating say task with non-string text."""
        is_valid, error = validate_task_params("say", {"text": 123})
        assert is_valid is False
        assert "'text' must be a string" in error

    def test_validate_notification_valid(self):
        """Test validating notification task with valid message."""
        is_valid, error = validate_task_params("notification", {"message": "Hello"})
        assert is_valid is True
        assert error == ""

    def test_validate_notification_missing_message(self):
        """Test validating notification task without message."""
        is_valid, error = validate_task_params("notification", {})
        assert is_valid is False
        assert "Missing 'message' parameter" in error

    def test_validate_set_clipboard_valid(self):
        """Test validating set_clipboard task with valid text."""
        is_valid, error = validate_task_params("set_clipboard", {"text": "Hello"})
        assert is_valid is True
        assert error == ""

    def test_validate_set_clipboard_missing_text(self):
        """Test validating set_clipboard task without text."""
        is_valid, error = validate_task_params("set_clipboard", {})
        assert is_valid is False
        assert "Missing 'text' parameter" in error

    def test_validate_run_script_valid(self):
        """Test validating run_script task with valid path."""
        is_valid, error = validate_task_params("run_script", {"path": "script.sh"})
        assert is_valid is True
        assert error == ""

    def test_validate_run_script_missing_path(self):
        """Test validating run_script task without path."""
        is_valid, error = validate_task_params("run_script", {})
        assert is_valid is False
        assert "Missing 'path' parameter" in error

    def test_validate_run_script_non_string_path(self):
        """Test validating run_script task with non-string path."""
        is_valid, error = validate_task_params("run_script", {"path": 123})
        assert is_valid is False
        assert "'path' must be a string" in error

    def test_validate_run_script_with_relative_path(self):
        """Test validating run_script task with relative path."""
        is_valid, error = validate_task_params("run_script", {"path": "../script.sh"})
        # Should still be valid but logged as warning
        assert is_valid is True

    def test_validate_screenshot_valid_full(self):
        """Test validating screenshot task with valid full type."""
        is_valid, error = validate_task_params("screenshot", {"type": "full"})
        assert is_valid is True
        assert error == ""

    def test_validate_screenshot_valid_window(self):
        """Test validating screenshot task with valid window type."""
        is_valid, error = validate_task_params("screenshot", {"type": "window"})
        assert is_valid is True
        assert error == ""

    def test_validate_screenshot_valid_selection(self):
        """Test validating screenshot task with valid selection type."""
        is_valid, error = validate_task_params("screenshot", {"type": "selection"})
        assert is_valid is True
        assert error == ""

    def test_validate_screenshot_invalid_type(self):
        """Test validating screenshot task with invalid type."""
        is_valid, error = validate_task_params("screenshot", {"type": "invalid"})
        assert is_valid is False
        assert "Invalid screenshot type" in error

    def test_validate_open_app_valid(self):
        """Test validating open_app task with valid app name."""
        is_valid, error = validate_task_params("open_app", {"app": "Safari"})
        assert is_valid is True
        assert error == ""

    def test_validate_open_app_missing_app(self):
        """Test validating open_app task without app."""
        is_valid, error = validate_task_params("open_app", {})
        assert is_valid is False
        assert "Missing 'app' parameter" in error

    def test_validate_open_app_non_string_app(self):
        """Test validating open_app task with non-string app."""
        is_valid, error = validate_task_params("open_app", {"app": 123})
        assert is_valid is False
        assert "'app' must be a string" in error

    def test_validate_unknown_task(self):
        """Test validating unknown task returns valid."""
        is_valid, error = validate_task_params("unknown_task", {})
        assert is_valid is True
        assert error == ""

