"""Tests for LMStudioClient service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import ChatMessage
from app.services.lmstudio_client import LMStudioClient


class TestLMStudioClient:
    """Test suite for LMStudioClient."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.client = LMStudioClient()

    def test_extract_reply_success(self) -> None:
        """Test extracting reply from valid response."""
        mock_data = {
            "choices": [
                {
                    "message": {
                        "content": "Test reply",
                    },
                },
            ],
        }
        reply = LMStudioClient.extract_reply(mock_data)
        assert reply == "Test reply"

    def test_extract_reply_failure(self) -> None:
        """Test extracting reply from invalid response."""
        mock_data = {"invalid": "structure"}
        reply = LMStudioClient.extract_reply(mock_data)
        assert "Sorry" in reply

    @pytest.mark.asyncio
    async def test_chat_success(self) -> None:
        """Test successful chat request."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test reply"}}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await self.client.chat("test message")

        assert "choices" in result

    @pytest.mark.asyncio
    async def test_chat_with_history(self) -> None:
        """Test chat request with history."""
        history = [
            ChatMessage(role="user", content="Previous message"),
            ChatMessage(role="assistant", content="Previous reply"),
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test reply"}}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await self.client.chat("test message", history=history)

        assert "choices" in result

