"""Tests for vision endpoint integration."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.services.lmstudio_client import LMStudioClient

client = TestClient(app)


class TestVisionEndpoint:
    """Test suite for vision endpoint."""

    def test_vision_without_image(self):
        """Test vision endpoint without image."""
        response = client.post(
            "/vision/analyze",
            json={"description": "Test description", "source": "test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "No image provided" in data["summary"]

    def test_vision_with_base64_image(self):
        """Test vision endpoint with base64 image."""
        # Create a simple test image (1x1 pixel PNG)
        test_image_data = base64.b64encode(b"fake image data").decode("utf-8")

        response = client.post(
            "/vision/analyze",
            json={
                "description": "What is in this image?",
                "image_base64": test_image_data,
                "source": "test",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "details" in data

    @pytest.mark.asyncio
    async def test_vision_client_method(self):
        """Test LMStudioClient.vision method."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test vision response"}}],
        }
        mock_response.raise_for_status = MagicMock()

        client_instance = LMStudioClient()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await client_instance.vision(
                image_base64="test_base64",
                description="Test description",
            )

        assert "choices" in result

    def test_vision_with_url(self):
        """Test vision endpoint with URL."""
        response = client.post(
            "/vision/analyze",
            json={
                "description": "Test description",
                "image_url": "https://example.com/image.jpg",
                "source": "test",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data

