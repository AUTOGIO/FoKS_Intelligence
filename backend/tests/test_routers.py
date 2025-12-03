"""Tests for API routers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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
        assert "env" in data


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

    def test_vision_with_description(self) -> None:
        """Test vision endpoint with description."""
        response = client.post(
            "/vision/analyze",
            json={"description": "Test image description", "source": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "details" in data


class TestTasksEndpoint:
    """Test suite for tasks endpoint."""

    def test_tasks_missing_task_name(self) -> None:
        """Test tasks endpoint with missing task_name."""
        response = client.post("/tasks/run", json={})
        assert response.status_code == 422

    def test_tasks_invalid_task(self) -> None:
        """Test tasks endpoint with invalid task."""
        response = client.post(
            "/tasks/run",
            json={"task_name": "invalid_task", "params": {}, "source": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_tasks_say_missing_params(self) -> None:
        """Test say task with missing parameters."""
        response = client.post(
            "/tasks/run",
            json={"task_name": "say", "params": {}, "source": "test"},
        )
        # Should return 400 Bad Request due to validation
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

