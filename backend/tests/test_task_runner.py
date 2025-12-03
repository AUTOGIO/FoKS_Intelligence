"""Tests for TaskRunner service."""

from __future__ import annotations

import pytest

from app.services.task_runner import TaskRunner


class TestTaskRunner:
    """Test suite for TaskRunner."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = TaskRunner()

    def test_open_url_success(self) -> None:
        """Test opening URL successfully."""
        result = self.runner.run("open_url", {"url": "https://www.apple.com"})
        assert result["success"] is True
        assert "Opened URL" in result["message"]

    def test_open_url_missing_param(self) -> None:
        """Test open_url with missing parameter."""
        result = self.runner.run("open_url", {})
        assert result["success"] is False
        assert "Missing" in result["message"]

    def test_say_success(self) -> None:
        """Test say task successfully."""
        result = self.runner.run("say", {"text": "test"})
        assert result["success"] is True

    def test_say_missing_param(self) -> None:
        """Test say with missing parameter."""
        result = self.runner.run("say", {})
        assert result["success"] is False
        assert "Missing" in result["message"]

    def test_notification_success(self) -> None:
        """Test notification task successfully."""
        result = self.runner.run(
            "notification",
            {"title": "Test", "message": "Test message", "subtitle": "Subtitle"},
        )
        assert result["success"] is True

    def test_notification_missing_message(self) -> None:
        """Test notification with missing message."""
        result = self.runner.run("notification", {"title": "Test"})
        assert result["success"] is False

    def test_get_clipboard_success(self) -> None:
        """Test get_clipboard task."""
        result = self.runner.run("get_clipboard", {})
        assert result["success"] is True
        assert "content" in result.get("data", {})

    def test_set_clipboard_success(self) -> None:
        """Test set_clipboard task."""
        result = self.runner.run("set_clipboard", {"text": "test content"})
        assert result["success"] is True

    def test_set_clipboard_missing_param(self) -> None:
        """Test set_clipboard with missing parameter."""
        result = self.runner.run("set_clipboard", {})
        assert result["success"] is False

    def test_open_app_success(self) -> None:
        """Test open_app task."""
        result = self.runner.run("open_app", {"app": "Notes"})
        assert result["success"] is True

    def test_open_app_missing_param(self) -> None:
        """Test open_app with missing parameter."""
        result = self.runner.run("open_app", {})
        assert result["success"] is False

    def test_unknown_task(self) -> None:
        """Test unknown task returns error."""
        result = self.runner.run("unknown_task", {})
        assert result["success"] is False
        assert "Unknown task" in result["message"]

    def test_run_script_success(self) -> None:
        """Test run_script task."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\necho 'test'\n")
            script_path = f.name
            os.chmod(script_path, 0o755)

        try:
            result = self.runner.run("run_script", {"path": script_path})
            assert result["success"] is True
        finally:
            os.unlink(script_path)

    def test_run_script_missing_param(self) -> None:
        """Test run_script with missing parameter."""
        result = self.runner.run("run_script", {})
        assert result["success"] is False

