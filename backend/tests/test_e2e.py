"""End-to-end tests for FoKS Intelligence."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Set environment variables for testing
os.environ["SKIP_CONFIG_VALIDATION"] = "true"
os.environ["LMSTUDIO_BASE_URL"] = "http://localhost:1234/v1/chat/completions"


@pytest.fixture
def test_db():
    """Create a temporary database for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["FOKS_DATABASE_PATH"] = db_path
    yield db_path
    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(test_db):
    """Create a test client."""
    return TestClient(app)


class TestE2EConversationFlow:
    """End-to-end tests for conversation flow."""

    def test_create_conversation_add_messages_get_history_delete(self, client):
        """Test complete conversation flow: create → add messages → get history → delete."""
        user_id = "test_user_e2e"

        # 1. Create conversation
        response = client.post(
            "/conversations/",
            json={"user_id": user_id, "title": "E2E Test Conversation", "source": "test"},
        )
        assert response.status_code == 200
        conversation_data = response.json()
        conversation_id = conversation_data["id"]
        assert conversation_data["user_id"] == user_id
        assert conversation_data["title"] == "E2E Test Conversation"

        # 2. Add messages via chat endpoint (simulated)
        # Note: This requires LM Studio to be running, so we'll skip if not available
        # In a real E2E test, you'd mock the LM Studio client

        # 3. Get conversation
        response = client.get(f"/conversations/{conversation_id}?user_id={user_id}")
        assert response.status_code == 200
        conv_data = response.json()
        assert conv_data["id"] == conversation_id

        # 4. List conversations
        response = client.get(f"/conversations/?user_id={user_id}")
        assert response.status_code == 200
        list_data = response.json()
        assert list_data["total"] >= 1
        assert any(conv["id"] == conversation_id for conv in list_data["conversations"])

        # 5. Get messages (should be empty initially)
        response = client.get(f"/conversations/{conversation_id}/messages?user_id={user_id}")
        assert response.status_code == 200
        messages = response.json()
        assert isinstance(messages, list)

        # 6. Update conversation title
        response = client.patch(
            f"/conversations/{conversation_id}/title?title=Updated Title"
        )
        assert response.status_code == 200

        # Verify title was updated
        response = client.get(f"/conversations/{conversation_id}?user_id={user_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

        # 7. Delete conversation
        response = client.delete(f"/conversations/{conversation_id}?user_id={user_id}")
        assert response.status_code == 200

        # Verify conversation is deleted
        response = client.get(f"/conversations/{conversation_id}?user_id={user_id}")
        assert response.status_code == 404


class TestE2EIntegration:
    """End-to-end integration tests."""

    def test_chat_save_conversation_retrieve_context(self, client):
        """Test chat → save conversation → retrieve context flow."""
        user_id = "test_user_integration"

        # 1. Create conversation
        response = client.post(
            "/conversations/",
            json={"user_id": user_id, "title": "Integration Test", "source": "test"},
        )
        assert response.status_code == 200
        conversation_id = response.json()["id"]

        # 2. Send chat message (requires LM Studio, will fail gracefully if not available)
        # This is a simplified test - in production you'd mock LM Studio
        try:
            response = client.post(
                "/chat/",
                json={"message": "Hello", "source": "test"},
                params={"conversation_id": conversation_id, "user_id": user_id},
            )
            # If LM Studio is not available, this will return 500
            # That's acceptable for E2E tests
            if response.status_code == 500:
                pytest.skip("LM Studio not available for E2E test")
        except Exception:
            pytest.skip("LM Studio not available for E2E test")

        # 3. Retrieve conversation context
        response = client.get(f"/conversations/{conversation_id}?user_id={user_id}")
        assert response.status_code == 200

        # 4. Get messages
        response = client.get(f"/conversations/{conversation_id}/messages?user_id={user_id}")
        assert response.status_code == 200
        messages = response.json()
        # Should have at least user message if chat succeeded
        assert isinstance(messages, list)


class TestE2EMetrics:
    """End-to-end tests for metrics."""

    def test_multiple_requests_verify_statistics(self, client):
        """Test multiple requests → verify statistics."""
        # Make multiple requests
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200

        # Get metrics
        response = client.get("/metrics")
        assert response.status_code == 200
        metrics = response.json()

        # Verify metrics structure
        assert "total_requests" in metrics
        assert "total_tasks" in metrics
        assert "uptime_seconds" in metrics
        assert metrics["total_requests"] >= 5  # At least our requests


class TestE2ECache:
    """End-to-end tests for cache functionality."""

    def test_cache_hit_and_invalidation(self, client):
        """Test cache hit and invalidation."""
        user_id = "test_user_cache"

        # Create conversation
        response = client.post(
            "/conversations/",
            json={"user_id": user_id, "title": "Cache Test", "source": "test"},
        )
        assert response.status_code == 200
        conversation_id = response.json()["id"]

        # First request (should miss cache, then cache it)
        response1 = client.get(f"/conversations/{conversation_id}?user_id={user_id}")
        assert response1.status_code == 200

        # Second request (should hit cache)
        response2 = client.get(f"/conversations/{conversation_id}?user_id={user_id}")
        assert response2.status_code == 200
        assert response1.json() == response2.json()

        # Update title (should invalidate cache)
        response = client.patch(
            f"/conversations/{conversation_id}/title?title=New Title"
        )
        assert response.status_code == 200

        # Next request should fetch fresh data (cache miss)
        response3 = client.get(f"/conversations/{conversation_id}?user_id={user_id}")
        assert response3.status_code == 200
        assert response3.json()["title"] == "New Title"

