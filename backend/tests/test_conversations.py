"""Tests for conversation store and router."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.models.conversation import Base, SessionLocal, create_engine_instance
from app.services.conversation_store import ConversationStore

# Use temporary database for tests
TEST_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
TEST_DB.close()
os.environ["FOKS_DATABASE_PATH"] = TEST_DB.name
os.environ["SKIP_CONFIG_VALIDATION"] = "true"

from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Setup test database before each test."""
    # Recreate tables
    engine = create_engine_instance()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB.name):
        os.unlink(TEST_DB.name)


@pytest.fixture
def conversation_store_instance():
    """Create a conversation store instance."""
    return ConversationStore()


class TestConversationStore:
    """Test suite for ConversationStore."""

    def test_create_conversation(self, conversation_store_instance):
        """Test creating a conversation."""
        conv = conversation_store_instance.create_conversation(
            user_id="test_user",
            title="Test Conversation",
        )
        assert conv.id is not None
        assert conv.user_id == "test_user"
        assert conv.title == "Test Conversation"

    def test_get_conversation(self, conversation_store_instance):
        """Test getting a conversation."""
        conv = conversation_store_instance.create_conversation(
            user_id="test_user",
            title="Test",
        )
        retrieved = conversation_store_instance.get_conversation(conv.id)
        assert retrieved is not None
        assert retrieved.id == conv.id

    def test_list_conversations(self, conversation_store_instance):
        """Test listing conversations."""
        conversation_store_instance.create_conversation(user_id="test_user", title="Conv 1")
        conversation_store_instance.create_conversation(user_id="test_user", title="Conv 2")
        conversations = conversation_store_instance.list_conversations("test_user")
        assert len(conversations) == 2

    def test_add_message(self, conversation_store_instance):
        """Test adding a message."""
        conv = conversation_store_instance.create_conversation(user_id="test_user")
        msg = conversation_store_instance.add_message(conv.id, "user", "Hello")
        assert msg.id is not None
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_get_messages(self, conversation_store_instance):
        """Test getting messages."""
        conv = conversation_store_instance.create_conversation(user_id="test_user")
        conversation_store_instance.add_message(conv.id, "user", "Hello")
        conversation_store_instance.add_message(conv.id, "assistant", "Hi")
        messages = conversation_store_instance.get_messages(conv.id)
        assert len(messages) == 2

    def test_delete_conversation(self, conversation_store_instance):
        """Test deleting a conversation."""
        conv = conversation_store_instance.create_conversation(user_id="test_user")
        success = conversation_store_instance.delete_conversation(conv.id)
        assert success is True
        retrieved = conversation_store_instance.get_conversation(conv.id)
        assert retrieved is None

    def test_update_conversation_title(self, conversation_store_instance):
        """Test updating conversation title."""
        conv = conversation_store_instance.create_conversation(
            user_id="test_user",
            title="Old Title",
        )
        success = conversation_store_instance.update_conversation_title(conv.id, "New Title")
        assert success is True
        updated = conversation_store_instance.get_conversation(conv.id)
        assert updated.title == "New Title"


class TestConversationsRouter:
    """Test suite for conversations router."""

    def test_create_conversation_endpoint(self):
        """Test creating conversation via API."""
        response = client.post(
            "/conversations/",
            json={"user_id": "test_user", "title": "Test", "source": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user"
        assert data["title"] == "Test"

    def test_list_conversations_endpoint(self):
        """Test listing conversations via API."""
        # Create a conversation first
        client.post(
            "/conversations/",
            json={"user_id": "test_user", "source": "test"},
        )
        response = client.get("/conversations/?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert len(data["conversations"]) > 0

    def test_get_conversation_endpoint(self):
        """Test getting conversation via API."""
        # Create a conversation first
        create_response = client.post(
            "/conversations/",
            json={"user_id": "test_user", "source": "test"},
        )
        conv_id = create_response.json()["id"]

        response = client.get(f"/conversations/{conv_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id

    def test_delete_conversation_endpoint(self):
        """Test deleting conversation via API."""
        # Create a conversation first
        create_response = client.post(
            "/conversations/",
            json={"user_id": "test_user", "source": "test"},
        )
        conv_id = create_response.json()["id"]

        response = client.delete(f"/conversations/{conv_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted
        get_response = client.get(f"/conversations/{conv_id}")
        assert get_response.status_code == 404

