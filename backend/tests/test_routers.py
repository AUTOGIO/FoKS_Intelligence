"""Tests for API routers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test suite for health endpoint."""

    def test_health_check(self) -> None:
        """Test health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app" in data
        assert "environment" in data


class TestChatEndpoint:
    """Test suite for chat endpoint."""

    def test_chat_missing_message(self) -> None:
        """Test chat endpoint with missing message."""
        response = client.post("/chat/", json={})
        assert response.status_code == 422  # Validation error

    def test_chat_invalid_json(self) -> None:
        """Test chat endpoint with invalid JSON."""
        response = client.post("/chat/", json={"invalid": "data"})
        # Should either validate or return 422
        assert response.status_code in [422, 500]


class TestVisionEndpoint:
    """Test suite for vision endpoint."""

    def test_vision_missing_description(self) -> None:
        """Test vision endpoint with missing description."""
        response = client.post("/vision/analyze", json={})
        assert response.status_code == 422

    def test_vision_requires_image_base64(self) -> None:
        """Vision requests require base64 image payload."""
        response = client.post(
            "/vision/analyze",
            json={"description": "Test image description", "source": "test"},
        )
        assert response.status_code == 400

    def test_vision_with_base64(self, monkeypatch) -> None:
        """Vision endpoint delegates to service layer."""
        from app.routers import vision as vision_router

        fake_result = {
            "model": "qwen3-vision-mlx",
            "provider": "lmstudio",
            "duration_ms": 10,
            "response": "Cute cat detected",
        }
        monkeypatch.setattr(
            vision_router.vision_service,
            "analyze_image",
            AsyncMock(return_value=fake_result),
        )

        response = client.post(
            "/vision/analyze",
            json={
                "description": "Test image description",
                "image_base64": "aGVsbG8=",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Cute cat detected"
        assert data["details"]["model"] == "qwen3-vision-mlx"


class TestTasksEndpoint:
    """Test suite for tasks endpoint."""

    def test_tasks_missing_type(self) -> None:
        """Task endpoint validation for missing type."""
        response = client.post("/tasks/run", json={})
        assert response.status_code == 422

    def test_tasks_delegates_to_runner(self, monkeypatch) -> None:
        """Router should delegate execution to task runner."""
        from app.routers import tasks as tasks_router

        fake_runner = MagicMock()
        fake_runner.run_task = AsyncMock(
            return_value={
                "task": "run_shell",
                "success": True,
                "duration_ms": 1,
                "payload": {"stdout": "hi"},
                "error": None,
            }
        )
        monkeypatch.setattr(tasks_router, "task_runner", fake_runner)

        response = client.post(
            "/tasks/run",
            json={"type": "run_shell", "args": {"cmd": "echo hi"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        tasks_router.task_runner.run_task.assert_awaited()

    def test_tasks_returns_error_envelope(self, monkeypatch) -> None:
        """Router returns structured error envelope from task runner."""
        from app.routers import tasks as tasks_router

        fake_runner = MagicMock()
        fake_runner.run_task = AsyncMock(
            return_value={
                "task": "run_shell",
                "success": False,
                "duration_ms": 1,
                "payload": {},
                "error": "boom",
            }
        )
        monkeypatch.setattr(tasks_router, "task_runner", fake_runner)

        response = client.post(
            "/tasks/run",
            json={"type": "run_shell", "args": {"cmd": "echo hi"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "boom"

